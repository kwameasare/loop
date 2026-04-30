"""Cost rollup with per-dimension aggregation (S281, S282).

S281: month-to-date aggregate per workspace.
S282: per-(agent, channel, model) breakdown.

Composes with ``UsageEvent`` from ``loop_control_plane.usage`` but adds
the optional ``agent_id``, ``channel``, ``model`` dimensions on a separate
``DimensionedUsageEvent`` model so the existing billing integration keeps
its narrower contract.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "CostBreakdown",
    "CostRollupService",
    "DimensionedUsageEvent",
    "MonthlyCost",
    "month_bucket_start_ms",
]


def month_bucket_start_ms(ts_ms: int) -> int:
    """Return the UTC midnight at the first day of the month containing ts_ms."""

    dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=UTC)
    first = datetime(dt.year, dt.month, 1, tzinfo=UTC)
    return int(first.timestamp() * 1000)


class DimensionedUsageEvent(BaseModel):
    """Cost-bearing usage observation tagged with the dimensions S282 cares about."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    workspace_id: UUID
    agent_id: UUID | None = None
    channel: str | None = Field(default=None, max_length=64)
    model: str | None = Field(default=None, max_length=128)
    metric: str = Field(min_length=1)
    cost_usd_micro: int = Field(ge=0)  # whole-microUSD; avoids float drift
    timestamp_ms: int = Field(ge=0)


@dataclass(frozen=True)
class CostBreakdown:
    """Aggregate row keyed by (workspace, agent, channel, model, metric)."""

    workspace_id: UUID
    agent_id: UUID | None
    channel: str | None
    model: str | None
    metric: str
    cost_usd_micro: int

    @property
    def cost_usd(self) -> float:
        return self.cost_usd_micro / 1_000_000.0


@dataclass(frozen=True)
class MonthlyCost:
    """Per-workspace MTD aggregate."""

    workspace_id: UUID
    month_start_ms: int
    cost_usd_micro: int

    @property
    def cost_usd(self) -> float:
        return self.cost_usd_micro / 1_000_000.0


@dataclass
class CostRollupService:
    """Compute MTD + per-dimension cost rollups from a ledger of events."""

    _events: list[DimensionedUsageEvent] = field(default_factory=list)

    def append(self, event: DimensionedUsageEvent) -> None:
        self._events.append(event)

    def extend(self, events: Iterable[DimensionedUsageEvent]) -> None:
        self._events.extend(events)

    # ----- S281 ----------------------------------------------------------
    def month_to_date(self, *, workspace_id: UUID, now_ms: int) -> MonthlyCost:
        start = month_bucket_start_ms(now_ms)
        total = sum(
            e.cost_usd_micro
            for e in self._events
            if e.workspace_id == workspace_id
            and start <= e.timestamp_ms <= now_ms
        )
        return MonthlyCost(
            workspace_id=workspace_id,
            month_start_ms=start,
            cost_usd_micro=total,
        )

    def projected_eom(
        self,
        *,
        workspace_id: UUID,
        now_ms: int,
        month_length_ms: int,
    ) -> int:
        """Linear extrapolation from MTD spend.

        Returns projected end-of-month cost in microUSD.
        """

        if month_length_ms <= 0:
            return 0
        mtd = self.month_to_date(workspace_id=workspace_id, now_ms=now_ms)
        elapsed = now_ms - mtd.month_start_ms
        if elapsed <= 0:
            return 0
        return int(mtd.cost_usd_micro * (month_length_ms / elapsed))

    # ----- S282 ----------------------------------------------------------
    def breakdown(
        self,
        *,
        workspace_id: UUID,
        start_ms: int,
        end_ms: int,
    ) -> tuple[CostBreakdown, ...]:
        """Aggregate events in [start_ms, end_ms] by full dimension tuple."""

        keys: dict[
            tuple[UUID, UUID | None, str | None, str | None, str],
            int,
        ] = {}
        for ev in self._events:
            if ev.workspace_id != workspace_id:
                continue
            if not (start_ms <= ev.timestamp_ms <= end_ms):
                continue
            key = (ev.workspace_id, ev.agent_id, ev.channel, ev.model, ev.metric)
            keys[key] = keys.get(key, 0) + ev.cost_usd_micro
        rows = [
            CostBreakdown(
                workspace_id=k[0],
                agent_id=k[1],
                channel=k[2],
                model=k[3],
                metric=k[4],
                cost_usd_micro=v,
            )
            for k, v in keys.items()
        ]
        rows.sort(
            key=lambda r: (
                str(r.agent_id) if r.agent_id else "",
                r.channel or "",
                r.model or "",
                r.metric,
            )
        )
        return tuple(rows)
