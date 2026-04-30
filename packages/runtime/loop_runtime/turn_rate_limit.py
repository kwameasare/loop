"""Per-workspace + per-agent rate limit on the runtime hot-path (S139).

Composes the cp-api ``RateLimiter`` (S117) with two key shapes:

  - ``ws:{workspace_id}`` -- coarse workspace ceiling
  - ``ws:{workspace_id}:agent:{agent_id}`` -- per-agent slice

A turn is admitted only if BOTH buckets have capacity. We do not refund the
workspace token on agent-bucket rejection because callers retry with a 429
and the brief over-debit is bounded by the refill rate.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from loop_control_plane.rate_limit import RateLimiter

__all__ = [
    "TurnRateLimitDecision",
    "TurnRateLimiter",
]


@dataclass(frozen=True)
class TurnRateLimitDecision:
    """Why a turn was admitted or rejected. Useful for 429 telemetry."""

    admitted: bool
    workspace_ok: bool
    agent_ok: bool

    @property
    def reason(self) -> str:
        if self.admitted:
            return "ok"
        if not self.workspace_ok:
            return "workspace_budget_exceeded"
        return "agent_budget_exceeded"


@dataclass
class TurnRateLimiter:
    """Two-tier rate limiter for runtime turn admission."""

    workspace_limiter: RateLimiter
    agent_limiter: RateLimiter

    async def admit(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        cost: float = 1.0,
    ) -> TurnRateLimitDecision:
        ws_key = f"ws:{workspace_id}"
        agent_key = f"ws:{workspace_id}:agent:{agent_id}"
        ws_ok = await self.workspace_limiter.try_consume(ws_key, cost=cost)
        if not ws_ok:
            return TurnRateLimitDecision(
                admitted=False, workspace_ok=False, agent_ok=False
            )
        agent_ok = await self.agent_limiter.try_consume(agent_key, cost=cost)
        return TurnRateLimitDecision(
            admitted=agent_ok, workspace_ok=True, agent_ok=agent_ok
        )
