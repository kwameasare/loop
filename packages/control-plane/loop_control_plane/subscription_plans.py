"""Subscription plan registry + canonical seed (S321).

Plans are pure data: the cp_0003 migration seeds the same rows. We
keep the canonical definition here so unit tests, smoke scripts, and
the migration generator all agree.

Caps are expressed in:

* ``daily_cost_usd_micro`` — used by the gateway/dp-runtime budget
  guard (S330) so we don't cross between dollars/cents/micros at the
  tier boundary; ``cost_rollup`` already speaks micro-USD.
* ``monthly_turn_cap`` — turn count cap; ``None`` means uncapped.
* ``rps_per_workspace`` / ``rps_per_agent`` — feed into the
  ``RateLimiter`` capacity/refill at request time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PlanTier = Literal["hobby", "pro", "team", "enterprise"]


@dataclass(frozen=True)
class Plan:
    tier: PlanTier
    daily_cost_usd_micro: int  # 0 = no cap
    monthly_turn_cap: int | None
    rps_per_workspace: float
    rps_per_agent: float
    seats: int  # included team seats


# Canonical seed — must match cp_0003 migration insert. Numbers picked
# to give clean boundaries for the S330 enforcement test.
_SEED: tuple[Plan, ...] = (
    Plan(
        tier="hobby",
        daily_cost_usd_micro=5_000_000,  # $5/day
        monthly_turn_cap=10_000,
        rps_per_workspace=2.0,
        rps_per_agent=1.0,
        seats=1,
    ),
    Plan(
        tier="pro",
        daily_cost_usd_micro=50_000_000,  # $50/day
        monthly_turn_cap=200_000,
        rps_per_workspace=20.0,
        rps_per_agent=10.0,
        seats=5,
    ),
    Plan(
        tier="team",
        daily_cost_usd_micro=500_000_000,  # $500/day
        monthly_turn_cap=2_000_000,
        rps_per_workspace=100.0,
        rps_per_agent=50.0,
        seats=20,
    ),
    Plan(
        tier="enterprise",
        daily_cost_usd_micro=0,  # uncapped — billed by contract
        monthly_turn_cap=None,
        rps_per_workspace=1000.0,
        rps_per_agent=500.0,
        seats=200,
    ),
)


class UnknownPlanError(KeyError):
    """Raised on lookup of a tier that isn't in the seed."""


def seed_plans() -> tuple[Plan, ...]:
    """The canonical plan list, ordered cheapest → richest."""

    return _SEED


def get_plan(tier: str) -> Plan:
    for plan in _SEED:
        if plan.tier == tier:
            return plan
    raise UnknownPlanError(f"unknown plan tier: {tier!r}")


__all__ = [
    "Plan",
    "PlanTier",
    "UnknownPlanError",
    "get_plan",
    "seed_plans",
]
