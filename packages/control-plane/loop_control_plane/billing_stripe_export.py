"""Nightly Stripe usage export (S325).

Loop's runtime writes per-turn usage rows to ClickHouse. Stripe's
metered-billing model wants aggregated quantities posted to a
``meter_event`` endpoint with an idempotency key per (workspace,
period). This module is the nightly aggregator + poster.

* Pure data flow — both ClickHouse and Stripe are Protocols so the
  exporter is unit-tested without external services.
* Idempotency — same workspace+period always emits the same key, so
  a retry never double-charges.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

UTC = UTC

DEFAULT_METRIC_NAMES: tuple[str, ...] = (
    "messages",
    "tool_calls",
    "voice_seconds",
    "tokens_input",
    "tokens_output",
)


class StripeExportError(RuntimeError):
    """Aggregation or push to Stripe failed."""


@dataclass(frozen=True, slots=True)
class UsageWindow:
    workspace_id: UUID
    period_start_ms: int
    period_end_ms: int

    def __post_init__(self) -> None:
        if self.period_end_ms <= self.period_start_ms:
            raise StripeExportError(
                "period_end_ms must be > period_start_ms"
            )


@dataclass(frozen=True, slots=True)
class UsageQuantity:
    metric: str
    quantity: int  # integer units posted to Stripe

    def __post_init__(self) -> None:
        if not self.metric:
            raise StripeExportError("metric required")
        if self.quantity < 0:
            raise StripeExportError("quantity must be >=0")


@runtime_checkable
class UsageQuery(Protocol):
    """ClickHouse-shaped read surface."""

    async def aggregate(
        self, *, window: UsageWindow, metrics: Sequence[str]
    ) -> dict[str, int]: ...


@dataclass(frozen=True, slots=True)
class StripeMeterEvent:
    """One row posted to Stripe's ``meter_events`` endpoint."""

    workspace_id: UUID
    metric: str
    quantity: int
    period_start_ms: int
    period_end_ms: int
    idempotency_key: str


@runtime_checkable
class StripeMeterClient(Protocol):
    async def post_meter_event(self, event: StripeMeterEvent) -> str: ...


def idempotency_key(*, workspace_id: UUID, metric: str, period_start_ms: int, period_end_ms: int) -> str:
    """Stable per-row idempotency key."""
    payload = f"{workspace_id.hex}:{metric}:{period_start_ms}:{period_end_ms}"
    return "loop-meter-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


@dataclass(slots=True)
class StripeUsageExporter:
    """Pull usage from ClickHouse, post to Stripe, return the IDs."""

    usage: UsageQuery
    stripe: StripeMeterClient
    metrics: tuple[str, ...] = DEFAULT_METRIC_NAMES

    def __post_init__(self) -> None:
        if not self.metrics:
            raise StripeExportError("metrics tuple must be non-empty")
        if len(set(self.metrics)) != len(self.metrics):
            raise StripeExportError("metric names must be unique")

    async def export(self, window: UsageWindow) -> list[StripeMeterEvent]:
        try:
            quantities = await self.usage.aggregate(window=window, metrics=self.metrics)
        except StripeExportError:
            raise
        except Exception as exc:
            raise StripeExportError(f"usage aggregate failed: {exc}") from exc
        events: list[StripeMeterEvent] = []
        for metric in self.metrics:
            qty = int(quantities.get(metric, 0))
            if qty <= 0:
                continue
            event = StripeMeterEvent(
                workspace_id=window.workspace_id,
                metric=metric,
                quantity=qty,
                period_start_ms=window.period_start_ms,
                period_end_ms=window.period_end_ms,
                idempotency_key=idempotency_key(
                    workspace_id=window.workspace_id,
                    metric=metric,
                    period_start_ms=window.period_start_ms,
                    period_end_ms=window.period_end_ms,
                ),
            )
            try:
                await self.stripe.post_meter_event(event)
            except Exception as exc:
                raise StripeExportError(
                    f"stripe.post_meter_event failed for {metric}: {exc}"
                ) from exc
            events.append(event)
        return events


def yesterday_window_utc(*, workspace_id: UUID, now_ms: int) -> UsageWindow:
    """Build a 24-hour UTC window ending at the most recent UTC midnight
    before ``now_ms``."""
    now = datetime.fromtimestamp(now_ms / 1000, tz=UTC)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_ms = int(midnight.timestamp() * 1000)
    start_ms = end_ms - 24 * 60 * 60 * 1000
    return UsageWindow(
        workspace_id=workspace_id, period_start_ms=start_ms, period_end_ms=end_ms
    )


__all__ = [
    "DEFAULT_METRIC_NAMES",
    "StripeExportError",
    "StripeMeterClient",
    "StripeMeterEvent",
    "StripeUsageExporter",
    "UsageQuantity",
    "UsageQuery",
    "UsageWindow",
    "idempotency_key",
    "yesterday_window_utc",
]
