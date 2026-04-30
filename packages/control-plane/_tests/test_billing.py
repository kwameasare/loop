"""Tests for billing wire-up + usage rollup (S025)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from loop_control_plane import (
    BillingError,
    BillingService,
    InMemoryStripe,
    UsageEvent,
    UsageLedger,
    UsageRollup,
    aggregate,
)
from loop_control_plane.usage import DAY_MS


@pytest.mark.asyncio
async def test_ensure_customer_is_idempotent_per_workspace() -> None:
    stripe = InMemoryStripe()
    svc = BillingService(client=stripe)
    ws = uuid4()
    a = await svc.ensure_customer(workspace_id=ws, email="ops@acme.test")
    b = await svc.ensure_customer(workspace_id=ws, email="ops@acme.test")
    assert a.id == b.id
    assert len(stripe.customers) == 1


@pytest.mark.asyncio
async def test_record_usage_requires_existing_customer() -> None:
    svc = BillingService(client=InMemoryStripe())
    with pytest.raises(BillingError):
        await svc.record_usage(
            workspace_id=uuid4(), metric="tokens.in", quantity=10, timestamp_ms=0
        )


@pytest.mark.asyncio
async def test_record_usage_rejects_negative_quantity() -> None:
    svc = BillingService(client=InMemoryStripe())
    ws = uuid4()
    await svc.ensure_customer(workspace_id=ws, email="ops@acme.test")
    with pytest.raises(BillingError):
        await svc.record_usage(workspace_id=ws, metric="tokens.in", quantity=-1, timestamp_ms=0)


@pytest.mark.asyncio
async def test_draft_invoice_aggregates_only_in_window() -> None:
    stripe = InMemoryStripe()
    svc = BillingService(
        client=stripe,
        rates_cents_per_unit={"tokens.in": 1, "tokens.out": 3},
    )
    ws = uuid4()
    await svc.ensure_customer(workspace_id=ws, email="ops@acme.test")

    # in window
    await svc.record_usage(workspace_id=ws, metric="tokens.in", quantity=100, timestamp_ms=10)
    await svc.record_usage(workspace_id=ws, metric="tokens.out", quantity=50, timestamp_ms=20)
    # out of window
    await svc.record_usage(workspace_id=ws, metric="tokens.in", quantity=999, timestamp_ms=200)

    inv = await svc.draft_invoice(workspace_id=ws, period_start_ms=0, period_end_ms=100)
    # 100 * 1c + 50 * 3c = 250c
    assert inv.amount_cents == 250
    assert dict(inv.line_items) == {"tokens.in": 100, "tokens.out": 150}


def test_aggregate_buckets_per_day_and_metric() -> None:
    ws = uuid4()
    events = [
        UsageEvent(workspace_id=ws, metric="tokens.in", quantity=10, timestamp_ms=0),
        UsageEvent(workspace_id=ws, metric="tokens.in", quantity=15, timestamp_ms=1_000),
        UsageEvent(workspace_id=ws, metric="tokens.out", quantity=2, timestamp_ms=DAY_MS + 5),
    ]
    out = aggregate(events)
    assert out[(ws, "tokens.in", 0)] == 25
    assert out[(ws, "tokens.out", DAY_MS)] == 2


@pytest.mark.asyncio
async def test_nightly_rollup_pushes_one_record_per_bucket() -> None:
    ws = uuid4()
    stripe = InMemoryStripe()
    svc = BillingService(client=stripe)
    await svc.ensure_customer(workspace_id=ws, email="ops@acme.test")

    ledger = UsageLedger()
    # Day 1 = [DAY_MS, 2*DAY_MS)
    ledger.append(
        UsageEvent(workspace_id=ws, metric="tokens.in", quantity=10, timestamp_ms=DAY_MS + 100)
    )
    ledger.append(
        UsageEvent(workspace_id=ws, metric="tokens.in", quantity=5, timestamp_ms=DAY_MS + 200)
    )
    ledger.append(
        UsageEvent(workspace_id=ws, metric="tokens.out", quantity=3, timestamp_ms=DAY_MS + 300)
    )
    # Day 2 -- should NOT roll up when nightly_rollup runs at end of day 1
    ledger.append(
        UsageEvent(workspace_id=ws, metric="tokens.in", quantity=99, timestamp_ms=2 * DAY_MS + 5)
    )

    rollup = UsageRollup(ledger=ledger, billing=svc)
    pushed = await rollup.nightly_rollup(now_ms=2 * DAY_MS)
    assert pushed == 2  # tokens.in + tokens.out for day 1
    assert len(stripe.usage) == 2
    qty_in = next(r.quantity for r in stripe.usage if r.metric == "tokens.in")
    qty_out = next(r.quantity for r in stripe.usage if r.metric == "tokens.out")
    assert qty_in == 15
    assert qty_out == 3


@pytest.mark.asyncio
async def test_nightly_rollup_is_safe_with_no_events() -> None:
    ws = uuid4()
    stripe = InMemoryStripe()
    svc = BillingService(client=stripe)
    await svc.ensure_customer(workspace_id=ws, email="ops@acme.test")
    rollup = UsageRollup(ledger=UsageLedger(), billing=svc)
    assert await rollup.nightly_rollup(now_ms=DAY_MS) == 0
    assert stripe.usage == []
