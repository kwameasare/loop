"""Plan-tier rate-limit + daily-cost enforcement (S330).

This composes ``RateLimiter`` (S117) for request-rate policing with a
running daily cost ledger that ``cost_rollup`` populates. Both gates
must pass for a turn to be admitted; the decision surfaces *which*
gate said no so the gateway / dp-runtime can map to the right error
code (LOOP-RT-301 for rate, LOOP-BIL-301 for budget).

The ledger is intentionally a tiny dict-of-dict in-process structure;
production wires the same Protocol against ClickHouse cost views via
a thin adapter.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, Protocol
from uuid import UUID

from loop_control_plane.rate_limit import RateLimiter
from loop_control_plane.subscription_plans import Plan

PlanGateReason = Literal[
    "ok",
    "workspace_rate_exceeded",
    "agent_rate_exceeded",
    "daily_cost_exceeded",
]


@dataclass(frozen=True)
class PlanGateDecision:
    admitted: bool
    reason: PlanGateReason
    daily_cost_usd_micro: int
    daily_cap_usd_micro: int  # 0 = uncapped


class DailyCostLedger(Protocol):
    def cost_today(self, workspace_id: UUID, *, now_ms: int) -> int: ...


@dataclass
class InMemoryDailyCostLedger:
    """Test double for ``DailyCostLedger``.

    Stores a flat ``(workspace_id, day_bucket) -> micro_usd`` map so we
    don't need ClickHouse in the unit tests.
    """

    _by_day: dict[tuple[UUID, int], int] = field(default_factory=dict)

    @staticmethod
    def _day_bucket(now_ms: int) -> int:
        return now_ms // (24 * 60 * 60 * 1000)

    def add(self, workspace_id: UUID, *, cost_usd_micro: int, now_ms: int) -> None:
        if cost_usd_micro < 0:
            raise ValueError("cost_usd_micro must be >= 0")
        key = (workspace_id, self._day_bucket(now_ms))
        self._by_day[key] = self._by_day.get(key, 0) + cost_usd_micro

    def cost_today(self, workspace_id: UUID, *, now_ms: int) -> int:
        return self._by_day.get((workspace_id, self._day_bucket(now_ms)), 0)


@dataclass
class PlanLimitGuard:
    """Two-axis admission gate: rate (per workspace + per agent) and
    daily cost.

    A new ``RateLimiter`` is built per workspace+agent on first use and
    cached. Capacity is sized to the plan's ``rps_per_*`` x 60 (one
    minute of bursting) with refill at ``rps`` per second.
    """

    plan_lookup: Mapping[UUID, Plan]
    ledger: DailyCostLedger
    _ws_limiters: dict[UUID, RateLimiter] = field(default_factory=dict)
    _agent_limiters: dict[tuple[UUID, UUID], RateLimiter] = field(default_factory=dict)

    def _plan_for(self, workspace_id: UUID) -> Plan:
        try:
            return self.plan_lookup[workspace_id]
        except KeyError as exc:
            raise PlanGateError(
                f"no plan registered for workspace {workspace_id}"
            ) from exc

    def _ws_limiter(self, workspace_id: UUID, plan: Plan) -> RateLimiter:
        existing = self._ws_limiters.get(workspace_id)
        if existing is not None:
            return existing
        limiter = RateLimiter(
            capacity=plan.rps_per_workspace * 60.0,
            refill_per_sec=plan.rps_per_workspace,
        )
        self._ws_limiters[workspace_id] = limiter
        return limiter

    def _agent_limiter(
        self, workspace_id: UUID, agent_id: UUID, plan: Plan
    ) -> RateLimiter:
        key = (workspace_id, agent_id)
        existing = self._agent_limiters.get(key)
        if existing is not None:
            return existing
        limiter = RateLimiter(
            capacity=plan.rps_per_agent * 60.0,
            refill_per_sec=plan.rps_per_agent,
        )
        self._agent_limiters[key] = limiter
        return limiter

    async def admit(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        now_ms: int,
        cost: float = 1.0,
    ) -> PlanGateDecision:
        plan = self._plan_for(workspace_id)
        spent = self.ledger.cost_today(workspace_id, now_ms=now_ms)
        cap = plan.daily_cost_usd_micro
        if cap and spent >= cap:
            return PlanGateDecision(
                admitted=False,
                reason="daily_cost_exceeded",
                daily_cost_usd_micro=spent,
                daily_cap_usd_micro=cap,
            )
        ws_ok = await self._ws_limiter(workspace_id, plan).try_consume(
            f"ws:{workspace_id}", cost=cost
        )
        if not ws_ok:
            return PlanGateDecision(
                admitted=False,
                reason="workspace_rate_exceeded",
                daily_cost_usd_micro=spent,
                daily_cap_usd_micro=cap,
            )
        agent_ok = await self._agent_limiter(
            workspace_id, agent_id, plan
        ).try_consume(f"ws:{workspace_id}:agent:{agent_id}", cost=cost)
        if not agent_ok:
            return PlanGateDecision(
                admitted=False,
                reason="agent_rate_exceeded",
                daily_cost_usd_micro=spent,
                daily_cap_usd_micro=cap,
            )
        return PlanGateDecision(
            admitted=True,
            reason="ok",
            daily_cost_usd_micro=spent,
            daily_cap_usd_micro=cap,
        )


class PlanGateError(RuntimeError):
    """Misconfiguration: workspace has no plan in the lookup."""


__all__ = [
    "DailyCostLedger",
    "InMemoryDailyCostLedger",
    "PlanGateDecision",
    "PlanGateError",
    "PlanGateReason",
    "PlanLimitGuard",
]
