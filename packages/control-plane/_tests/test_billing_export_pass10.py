"""Tests for pass10 Stripe usage export (S325)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from loop_control_plane.billing_stripe_export import (
    DEFAULT_METRIC_NAMES,
    StripeExportError,
    StripeMeterEvent,
    StripeUsageExporter,
    UsageQuantity,
    UsageWindow,
    idempotency_key,
    yesterday_window_utc,
)


def test_usage_window_rejects_non_increasing():
    with pytest.raises(StripeExportError):
        UsageWindow(workspace_id=uuid4(), period_start_ms=10, period_end_ms=10)
    with pytest.raises(StripeExportError):
        UsageWindow(workspace_id=uuid4(), period_start_ms=20, period_end_ms=10)


def test_usage_quantity_validators():
    with pytest.raises(StripeExportError):
        UsageQuantity(metric="", quantity=0)
    with pytest.raises(StripeExportError):
        UsageQuantity(metric="x", quantity=-1)


def test_idempotency_key_is_deterministic():
    ws = uuid4()
    k1 = idempotency_key(workspace_id=ws, metric="m", period_start_ms=1, period_end_ms=2)
    k2 = idempotency_key(workspace_id=ws, metric="m", period_start_ms=1, period_end_ms=2)
    k3 = idempotency_key(workspace_id=ws, metric="m", period_start_ms=1, period_end_ms=3)
    assert k1 == k2
    assert k1 != k3
    assert k1.startswith("loop-meter-")


class FakeUsage:
    def __init__(self, quantities):
        self.quantities = quantities
        self.calls: list[dict] = []

    async def aggregate(self, *, window, metrics):
        self.calls.append({"window": window, "metrics": tuple(metrics)})
        return dict(self.quantities)


class FakeStripe:
    def __init__(self):
        self.events: list[StripeMeterEvent] = []

    async def post_meter_event(self, event):
        self.events.append(event)
        return event.idempotency_key


@pytest.mark.asyncio
async def test_export_skips_zero_metrics():
    ws = uuid4()
    window = UsageWindow(workspace_id=ws, period_start_ms=0, period_end_ms=100)
    usage = FakeUsage({"messages": 12, "tool_calls": 0, "voice_seconds": 5,
                       "tokens_input": 0, "tokens_output": 9})
    stripe = FakeStripe()
    exporter = StripeUsageExporter(usage=usage, stripe=stripe)
    events = await exporter.export(window)
    metrics_emitted = sorted(e.metric for e in events)
    assert metrics_emitted == ["messages", "tokens_output", "voice_seconds"]
    assert {e.metric for e in stripe.events} == set(metrics_emitted)


@pytest.mark.asyncio
async def test_export_propagates_stripe_failure():
    ws = uuid4()
    window = UsageWindow(workspace_id=ws, period_start_ms=0, period_end_ms=100)
    usage = FakeUsage({"messages": 1})

    class BadStripe:
        async def post_meter_event(self, event):
            raise RuntimeError("rate-limited")

    exporter = StripeUsageExporter(usage=usage, stripe=BadStripe(), metrics=("messages",))
    with pytest.raises(StripeExportError):
        await exporter.export(window)


@pytest.mark.asyncio
async def test_export_propagates_aggregate_failure():
    class BadUsage:
        async def aggregate(self, *, window, metrics):
            raise RuntimeError("clickhouse down")

    exporter = StripeUsageExporter(usage=BadUsage(), stripe=FakeStripe())
    window = UsageWindow(workspace_id=uuid4(), period_start_ms=0, period_end_ms=100)
    with pytest.raises(StripeExportError):
        await exporter.export(window)


def test_exporter_rejects_empty_metrics():
    with pytest.raises(StripeExportError):
        StripeUsageExporter(usage=FakeUsage({}), stripe=FakeStripe(), metrics=())


def test_exporter_rejects_duplicate_metrics():
    with pytest.raises(StripeExportError):
        StripeUsageExporter(
            usage=FakeUsage({}), stripe=FakeStripe(), metrics=("a", "a")
        )


def test_yesterday_window_is_24h_aligned_to_midnight():
    ws = uuid4()
    # 2024-06-15 12:30 UTC → midnight 2024-06-15 = end, midnight 2024-06-14 = start
    now_ms = 1718454600000  # 2024-06-15T12:30:00Z
    window = yesterday_window_utc(workspace_id=ws, now_ms=now_ms)
    assert window.period_end_ms - window.period_start_ms == 24 * 60 * 60 * 1000
    assert window.period_end_ms <= now_ms
    # End is at UTC midnight
    assert window.period_end_ms % (24 * 60 * 60 * 1000) == 0


def test_default_metrics_present():
    assert "messages" in DEFAULT_METRIC_NAMES
    assert "tokens_input" in DEFAULT_METRIC_NAMES
    assert len(set(DEFAULT_METRIC_NAMES)) == len(DEFAULT_METRIC_NAMES)
