"""Tests for pass5 control-plane modules."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from uuid import uuid4

import pytest
from loop_control_plane.inbox import InboxQueue
from loop_control_plane.inbox_events import InboxEvent, InboxEventBus
from loop_control_plane.plan_limits import (
    InMemoryDailyCostLedger,
    PlanGateError,
    PlanLimitGuard,
)
from loop_control_plane.stripe_webhook import (
    StripeWebhookDispatcher,
    StripeWebhookError,
    parse_invoice_event,
    parse_subscription_event,
    verify_signature,
)
from loop_control_plane.subscription_plans import (
    UnknownPlanError,
    get_plan,
    seed_plans,
)
from loop_control_plane.suspension import (
    SuspensionService,
    WorkspaceSuspendedError,
)

# ---------------------------------------------------------------------------
# stripe_webhook (S322 + S323 + S324)
# ---------------------------------------------------------------------------


def _sign(secret: str, ts: int, payload: bytes) -> str:
    signed = f"{ts}.".encode() + payload
    return hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()


def _make_header(secret: str, ts: int, payload: bytes) -> str:
    return f"t={ts},v1={_sign(secret, ts, payload)}"


def test_stripe_signature_round_trip() -> None:
    secret = "whsec_test_123"  # noqa: S105
    payload = b'{"id":"evt_1","type":"ping","created":1700000000,"data":{"object":{}}}'
    ts = 1_700_000_000
    header = _make_header(secret, ts, payload)
    verify_signature(
        payload=payload,
        header=header,
        secret=secret,
        now_ms=ts * 1000,
    )


def test_stripe_signature_rejects_tamper() -> None:
    secret = "whsec_test_123"  # noqa: S105
    payload = b'{"hello":"world"}'
    ts = 1_700_000_000
    header = _make_header(secret, ts, payload)
    with pytest.raises(StripeWebhookError):
        verify_signature(
            payload=payload + b"x",
            header=header,
            secret=secret,
            now_ms=ts * 1000,
        )


def test_stripe_signature_rejects_stale() -> None:
    secret = "whsec"  # noqa: S105
    payload = b"{}"
    ts = 1_700_000_000
    header = _make_header(secret, ts, payload)
    with pytest.raises(StripeWebhookError):
        verify_signature(
            payload=payload,
            header=header,
            secret=secret,
            now_ms=(ts + 1000) * 1000,  # 1000s drift > 300s tolerance
        )


def test_stripe_dispatcher_routes_subscription_event() -> None:
    secret = "whsec_xyz"  # noqa: S105
    dispatcher = StripeWebhookDispatcher(secret=secret)
    seen: list[str] = []
    dispatcher.on(
        "customer.subscription.updated",
        lambda evt: seen.append(parse_subscription_event(evt).status),
    )
    body = {
        "id": "evt_sub_1",
        "type": "customer.subscription.updated",
        "created": 1_700_000_000,
        "data": {
            "object": {
                "id": "sub_abc",
                "customer": "cus_123",
                "status": "active",
                "items": {
                    "data": [{"price": {"id": "price_pro_monthly"}}]
                },
            }
        },
    }
    payload = json.dumps(body).encode("utf-8")
    ts = 1_700_000_000
    header = _make_header(secret, ts, payload)
    event = dispatcher.dispatch(
        payload=payload, header=header, now_ms=ts * 1000
    )
    assert event is not None
    assert seen == ["active"]
    # Idempotent on retry.
    assert (
        dispatcher.dispatch(payload=payload, header=header, now_ms=ts * 1000)
        is None
    )


def test_stripe_dispatcher_invoice_event_parses() -> None:
    secret = "whsec"  # noqa: S105
    dispatcher = StripeWebhookDispatcher(secret=secret)
    captured: list[int] = []
    dispatcher.on(
        "invoice.paid",
        lambda evt: captured.append(parse_invoice_event(evt).amount_paid_micro),
    )
    body = {
        "id": "evt_inv_1",
        "type": "invoice.paid",
        "created": 1,
        "data": {
            "object": {
                "id": "in_1",
                "customer": "cus_1",
                "paid": True,
                "amount_paid": 1234,  # cents
                "attempt_count": 1,
            }
        },
    }
    payload = json.dumps(body).encode("utf-8")
    ts = int(time.time())
    dispatcher.dispatch(
        payload=payload,
        header=_make_header(secret, ts, payload),
        now_ms=ts * 1000,
    )
    assert captured == [1234 * 10_000]


# ---------------------------------------------------------------------------
# subscription_plans (S321)
# ---------------------------------------------------------------------------


def test_seed_plans_includes_all_tiers() -> None:
    tiers = {p.tier for p in seed_plans()}
    assert tiers == {"hobby", "pro", "team", "enterprise"}


def test_get_plan_unknown_raises() -> None:
    with pytest.raises(UnknownPlanError):
        get_plan("ultra-premium-platinum")


def test_hobby_caps_match_ac() -> None:
    hobby = get_plan("hobby")
    # AC: hobby capped at $5/day → 5_000_000 µUSD.
    assert hobby.daily_cost_usd_micro == 5_000_000
    team = get_plan("team")
    assert team.daily_cost_usd_micro == 500_000_000


# ---------------------------------------------------------------------------
# plan_limits (S330)
# ---------------------------------------------------------------------------


def test_plan_gate_admits_within_budget_and_rate() -> None:
    ws = uuid4()
    agent = uuid4()
    plan = get_plan("hobby")
    ledger = InMemoryDailyCostLedger()
    guard = PlanLimitGuard(plan_lookup={ws: plan}, ledger=ledger)
    decision = asyncio.run(
        guard.admit(workspace_id=ws, agent_id=agent, now_ms=1_000)
    )
    assert decision.admitted is True
    assert decision.reason == "ok"


def test_plan_gate_blocks_when_daily_cap_exceeded() -> None:
    ws = uuid4()
    agent = uuid4()
    plan = get_plan("hobby")
    ledger = InMemoryDailyCostLedger()
    ledger.add(ws, cost_usd_micro=plan.daily_cost_usd_micro, now_ms=1_000)
    guard = PlanLimitGuard(plan_lookup={ws: plan}, ledger=ledger)
    decision = asyncio.run(
        guard.admit(workspace_id=ws, agent_id=agent, now_ms=1_000)
    )
    assert decision.admitted is False
    assert decision.reason == "daily_cost_exceeded"
    assert decision.daily_cost_usd_micro == plan.daily_cost_usd_micro


def test_plan_gate_unknown_workspace_raises() -> None:
    guard = PlanLimitGuard(plan_lookup={}, ledger=InMemoryDailyCostLedger())
    with pytest.raises(PlanGateError):
        asyncio.run(
            guard.admit(workspace_id=uuid4(), agent_id=uuid4(), now_ms=0)
        )


# ---------------------------------------------------------------------------
# suspension (S326)
# ---------------------------------------------------------------------------


def test_suspension_blocks_writes_until_reinstated() -> None:
    svc = SuspensionService()
    ws = uuid4()
    svc.check_writeable(ws)  # not suspended → OK
    svc.suspend(ws, reason="payment_failed", now_ms=10)
    with pytest.raises(WorkspaceSuspendedError) as exc:
        svc.check_writeable(ws)
    assert exc.value.reason == "payment_failed"
    assert exc.value.since_ms == 10
    # Suspend twice keeps the original timestamp.
    svc.suspend(ws, reason="manual", now_ms=999, note="ignored on idempotent")
    rec = svc.get(ws)
    assert rec is not None
    assert rec.since_ms == 10
    assert rec.reason == "payment_failed"
    assert svc.reinstate(ws) is True
    svc.check_writeable(ws)


# ---------------------------------------------------------------------------
# inbox_events + auto_release_idle (S304 + S305)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_inbox_event_bus_fans_out() -> None:
    bus = InboxEventBus()
    event = InboxEvent(
        workspace_id=uuid4(),
        item_id=uuid4(),
        conversation_id=uuid4(),
        kind="inbox.takeover_started",
        operator_id="op-1",
        timestamp_ms=42,
    )

    async def consume() -> InboxEvent:
        async with bus.subscribe() as stream:
            async for ev in stream:
                return ev
        raise AssertionError("no event yielded")

    task = asyncio.create_task(consume())
    await asyncio.sleep(0)  # let the subscriber register
    await bus.publish(event)
    received = await asyncio.wait_for(task, timeout=1.0)
    assert received == event


def test_inbox_auto_release_idle() -> None:
    queue = InboxQueue()
    ws, agent = uuid4(), uuid4()
    item = queue.escalate(
        workspace_id=ws,
        agent_id=agent,
        conversation_id=uuid4(),
        user_id="u-1",
        reason="needs human",
        now_ms=0,
    )
    queue.claim(item.id, operator_id="op-1", now_ms=100)
    # 14 minutes idle → still claimed.
    released = queue.auto_release_idle(
        idle_after_ms=15 * 60 * 1000, now_ms=100 + 14 * 60 * 1000
    )
    assert released == []
    # 16 minutes idle → released.
    released = queue.auto_release_idle(
        idle_after_ms=15 * 60 * 1000, now_ms=100 + 16 * 60 * 1000
    )
    assert len(released) == 1
    assert released[0].status == "pending"
    assert released[0].operator_id is None
