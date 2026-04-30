"""Multi-agent cost rollup (S407).

When a parent agent spawns child agent runs (the multi-agent
pattern from S404/S406), each child emits its own usage events.
The parent's *displayed* cost should be the parent-only spend, but
the *workspace* cost rollup must aggregate parent + all children.

This module produces both views from a single ``aggregate`` call.
The ``parent_turn_id`` field on each child usage event is the link
that survives across the SSE boundary (children stream to the
runtime, runtime tags them with the parent turn id, then forwards
to the cost-rollup pipeline).
"""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "MultiAgentCostRollup",
    "RollupResult",
    "TurnCostEvent",
]


class TurnCostEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    turn_id: UUID
    parent_turn_id: UUID | None = None
    cost_usd_micro: int = Field(ge=0)
    """Cost in micro-USD (1e-6 USD). int storage avoids float drift."""
    tokens_in: int = Field(ge=0)
    tokens_out: int = Field(ge=0)


class _ChildBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    turn_id: UUID
    cost_usd_micro: int


class RollupResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    parent_turn_id: UUID
    parent_cost_usd_micro: int = Field(ge=0)
    children_cost_usd_micro: int = Field(ge=0)
    total_cost_usd_micro: int = Field(ge=0)
    parent_tokens_in: int
    parent_tokens_out: int
    total_tokens_in: int
    total_tokens_out: int
    child_breakdown: tuple[_ChildBreakdown, ...]

    @property
    def total_cost_usd(self) -> float:
        return self.total_cost_usd_micro / 1_000_000


class MultiAgentCostRollup:
    """Aggregate parent + child cost events into a single rollup row."""

    @staticmethod
    def aggregate(
        *,
        parent: TurnCostEvent,
        children: Iterable[TurnCostEvent],
    ) -> RollupResult:
        if parent.parent_turn_id is not None:
            raise ValueError(
                f"parent {parent.turn_id} unexpectedly has parent_turn_id={parent.parent_turn_id}"
            )
        child_list = list(children)
        for c in child_list:
            if c.parent_turn_id != parent.turn_id:
                raise ValueError(
                    f"child {c.turn_id} parent_turn_id={c.parent_turn_id} does not match parent {parent.turn_id}"
                )
        children_cost = sum(c.cost_usd_micro for c in child_list)
        children_tin = sum(c.tokens_in for c in child_list)
        children_tout = sum(c.tokens_out for c in child_list)
        return RollupResult(
            parent_turn_id=parent.turn_id,
            parent_cost_usd_micro=parent.cost_usd_micro,
            children_cost_usd_micro=children_cost,
            total_cost_usd_micro=parent.cost_usd_micro + children_cost,
            parent_tokens_in=parent.tokens_in,
            parent_tokens_out=parent.tokens_out,
            total_tokens_in=parent.tokens_in + children_tin,
            total_tokens_out=parent.tokens_out + children_tout,
            child_breakdown=tuple(
                _ChildBreakdown(turn_id=c.turn_id, cost_usd_micro=c.cost_usd_micro)
                for c in child_list
            ),
        )
