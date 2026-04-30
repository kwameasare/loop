"""Usage rollup: nightly aggregation from raw turn telemetry to billing units.

The runtime + gateway emit per-turn usage events (input tokens, output tokens,
tool calls, retrievals). These are appended to an in-memory ledger. The
``UsageRollup`` service aggregates a 24-hour window per workspace and pushes
the result through ``BillingService.record_usage`` so Stripe (or its test
double) sees one usage record per (workspace, metric, day).

This module is intentionally storage-agnostic; production wiring will swap the
in-memory ledger for the Postgres ``usage_events`` table.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane.billing import BillingService

DAY_MS = 24 * 60 * 60 * 1000


class UsageEvent(BaseModel):
    """A raw usage observation produced by the runtime."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    workspace_id: UUID
    metric: str = Field(min_length=1)
    quantity: int = Field(ge=0)
    timestamp_ms: int = Field(ge=0)


def _day_bucket_start(ts_ms: int) -> int:
    return (ts_ms // DAY_MS) * DAY_MS


@dataclass
class UsageLedger:
    """Append-only in-memory ledger of usage events."""

    events: list[UsageEvent] = field(default_factory=list)

    def append(self, event: UsageEvent) -> None:
        self.events.append(event)

    def window(self, *, start_ms: int, end_ms: int) -> list[UsageEvent]:
        return [e for e in self.events if start_ms <= e.timestamp_ms < end_ms]


def aggregate(
    events: list[UsageEvent],
) -> dict[tuple[UUID, str, int], int]:
    """Aggregate events into ``(workspace, metric, day_bucket_ms) -> qty``."""

    buckets: dict[tuple[UUID, str, int], int] = {}
    for ev in events:
        key = (ev.workspace_id, ev.metric, _day_bucket_start(ev.timestamp_ms))
        buckets[key] = buckets.get(key, 0) + ev.quantity
    return buckets


@dataclass
class UsageRollup:
    """Nightly rollup job."""

    ledger: UsageLedger
    billing: BillingService

    async def nightly_rollup(self, *, now_ms: int) -> int:
        """Roll up the day ending at ``now_ms`` (UTC midnight aligned).

        Returns the number of usage records pushed to billing.
        """

        end = _day_bucket_start(now_ms)
        start = end - DAY_MS
        events = self.ledger.window(start_ms=start, end_ms=end)
        buckets = aggregate(events)
        pushed = 0
        for (workspace_id, metric, day_ms), qty in sorted(
            buckets.items(), key=lambda kv: (str(kv[0][0]), kv[0][1], kv[0][2])
        ):
            await self.billing.record_usage(
                workspace_id=workspace_id,
                metric=metric,
                quantity=qty,
                timestamp_ms=day_ms,
            )
            pushed += 1
        return pushed


__all__ = [
    "DAY_MS",
    "UsageEvent",
    "UsageLedger",
    "UsageRollup",
    "aggregate",
]
