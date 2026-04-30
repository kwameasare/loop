"""Pass9 voice tests: outbound call idempotency + phone number provisioning."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from loop_voice.outbound_call import (
    OutboundCallController,
    OutboundCallError,
    OutboundCallRequest,
)
from loop_voice.phone_provisioning import (
    PhoneNumberStore,
    PhoneProvisioningError,
    ProvisioningStatus,
)

# --- outbound_call -------------------------------------------------------


class _FakeDialer:
    def __init__(self, sid: str = "CA-fake-123"):
        self.sid = sid
        self.calls: list[dict] = []

    async def dial(self, *, from_number, to_number, opening_utterance):
        self.calls.append(
            {"from": from_number, "to": to_number, "open": opening_utterance}
        )
        return self.sid


def _req(**overrides) -> OutboundCallRequest:
    base = dict(
        workspace_id=uuid4(),
        agent_id=uuid4(),
        from_number="+15551110000",
        to_number="+15552221111",
        idempotency_key="key-1",
        opening_utterance="Hello",
    )
    base.update(overrides)
    return OutboundCallRequest(**base)


@pytest.mark.asyncio
async def test_place_dials_carrier_once():
    dialer = _FakeDialer()
    ctl = OutboundCallController(dialer=dialer)
    req = _req()
    ticket = await ctl.place(req)
    assert ticket.provider_call_sid == "CA-fake-123"
    assert ticket.workspace_id == req.workspace_id
    assert len(dialer.calls) == 1


@pytest.mark.asyncio
async def test_place_idempotent_on_replay():
    dialer = _FakeDialer()
    ctl = OutboundCallController(dialer=dialer)
    req = _req()
    a = await ctl.place(req)
    b = await ctl.place(req)
    assert a is b
    assert len(dialer.calls) == 1


@pytest.mark.asyncio
async def test_different_idempotency_keys_dial_twice():
    dialer = _FakeDialer()
    ctl = OutboundCallController(dialer=dialer)
    ws = uuid4()
    a = await ctl.place(_req(workspace_id=ws, idempotency_key="k-a"))
    b = await ctl.place(_req(workspace_id=ws, idempotency_key="k-b"))
    assert a.call_id != b.call_id
    assert len(dialer.calls) == 2


def test_request_rejects_invalid_e164():
    with pytest.raises(ValueError):
        _req(to_number="555-1234")


def test_request_rejects_zero_lead_country_code():
    with pytest.raises(ValueError):
        _req(to_number="+05551234567")


@pytest.mark.asyncio
async def test_carrier_failure_surfaces_typed_error():
    class _BoomDialer:
        async def dial(self, **_):
            raise RuntimeError("rate limit")

    ctl = OutboundCallController(dialer=_BoomDialer())
    with pytest.raises(OutboundCallError):
        await ctl.place(_req())


@pytest.mark.asyncio
async def test_empty_sid_raises():
    class _EmptyDialer:
        async def dial(self, **_):
            return ""

    ctl = OutboundCallController(dialer=_EmptyDialer())
    with pytest.raises(OutboundCallError):
        await ctl.place(_req())


# --- phone_provisioning --------------------------------------------------


def test_claim_first_time():
    store = PhoneNumberStore()
    ws = uuid4()
    rec = store.claim(e164="+15555550000", workspace_id=ws, carrier="twilio")
    assert rec.status is ProvisioningStatus.ACTIVE
    assert rec.released_at is None


def test_claim_conflict_when_active():
    store = PhoneNumberStore()
    store.claim(e164="+15555550000", workspace_id=uuid4(), carrier="twilio")
    with pytest.raises(PhoneProvisioningError):
        store.claim(e164="+15555550000", workspace_id=uuid4(), carrier="twilio")


def test_release_and_reclaim_allowed():
    store = PhoneNumberStore()
    ws_a = uuid4()
    ws_b = uuid4()
    store.claim(e164="+15555550000", workspace_id=ws_a, carrier="twilio")
    store.release(e164="+15555550000", workspace_id=ws_a)
    rec = store.claim(e164="+15555550000", workspace_id=ws_b, carrier="telnyx")
    assert rec.workspace_id == ws_b
    assert rec.carrier == "telnyx"
    assert rec.released_at is None
    assert rec.status is ProvisioningStatus.ACTIVE


def test_release_by_wrong_workspace_rejected():
    store = PhoneNumberStore()
    ws_a = uuid4()
    store.claim(e164="+15555550000", workspace_id=ws_a, carrier="twilio")
    with pytest.raises(PhoneProvisioningError):
        store.release(e164="+15555550000", workspace_id=uuid4())


def test_release_unclaimed_rejected():
    store = PhoneNumberStore()
    with pytest.raises(PhoneProvisioningError):
        store.release(e164="+15555550000", workspace_id=uuid4())


def test_list_active_scoped_per_workspace():
    store = PhoneNumberStore()
    ws_a = uuid4()
    ws_b = uuid4()
    store.claim(e164="+15555550001", workspace_id=ws_a, carrier="twilio")
    store.claim(e164="+15555550002", workspace_id=ws_b, carrier="twilio")
    store.claim(e164="+15555550003", workspace_id=ws_a, carrier="twilio")
    out = store.list_active(ws_a)
    assert [r.e164 for r in out] == ["+15555550001", "+15555550003"]


def test_invalid_e164_rejected_at_claim():
    store = PhoneNumberStore()
    with pytest.raises(PhoneProvisioningError):
        store.claim(e164="bad", workspace_id=uuid4(), carrier="twilio")


def test_get_returns_record():
    store = PhoneNumberStore()
    ws = uuid4()
    store.claim(e164="+15555550009", workspace_id=ws, carrier="twilio")
    rec = store.get("+15555550009")
    assert rec.workspace_id == ws


def test_records_use_aware_datetimes():
    store = PhoneNumberStore()
    rec = store.claim(
        e164="+15555550000",
        workspace_id=uuid4(),
        carrier="twilio",
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert rec.claimed_at.tzinfo is not None
