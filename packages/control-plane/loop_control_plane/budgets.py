"""Workspace budgets service (P0.4).

Gate per-workspace LLM spend so a runaway agent can't burn the
operator's quota. Production wires this into the runtime's preflight
check: every turn checks ``WorkspaceBudget.remaining_usd`` against
the gateway's pessimistic upper-bound estimate before kicking off
the LLM call.

The gateway already has the math (``loop_gateway.preflight``); this
module is the persistence layer + per-workspace policy.

Two budget shapes:
* ``daily_limit_usd`` — soft cap, resets at midnight UTC. Going over
  emits a ``degrade`` event but doesn't block.
* ``hard_limit_usd`` — block-after-spend cap. Exceeding it returns
  ``deny`` from preflight, no LLM call happens.

Both default to None (unbounded). The studio's "Costs" tab is the
read consumer; budget changes are admin-gated.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceBudget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    workspace_id: UUID
    daily_limit_usd: Decimal | None = Field(default=None, ge=Decimal(0))
    hard_limit_usd: Decimal | None = Field(default=None, ge=Decimal(0))
    spent_today_usd: Decimal = Field(default=Decimal(0), ge=Decimal(0))
    spent_total_usd: Decimal = Field(default=Decimal(0), ge=Decimal(0))


class BudgetUpdate(BaseModel):
    """Body for PATCH /v1/workspaces/{id}/budgets — partial update.

    Accepts JSON strings (``"10.00"``) for the limits because Pydantic
    can't safely round-trip a JSON ``number`` into ``Decimal`` (loses
    precision for >15 significant digits). Sending the value as a
    string preserves exact precision through the parser; we drop
    ``strict=True`` here because we deliberately *want* the
    ``str -> Decimal`` coercion that strict mode forbids.
    """

    model_config = ConfigDict(extra="forbid")
    daily_limit_usd: Decimal | None = Field(default=None, ge=Decimal(0))
    hard_limit_usd: Decimal | None = Field(default=None, ge=Decimal(0))


class BudgetError(ValueError):
    """Raised on invalid update payloads or unknown workspaces."""


@dataclass
class BudgetService:
    """In-memory per-workspace budget store. Production swaps for a
    Postgres-backed implementation against the ``workspace_budgets``
    table (planned for the Postgres-services milestone)."""

    _budgets: dict[UUID, WorkspaceBudget] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def get(self, workspace_id: UUID) -> WorkspaceBudget:
        async with self._lock:
            return self._budgets.get(
                workspace_id,
                WorkspaceBudget(workspace_id=workspace_id),
            )

    async def patch(
        self, workspace_id: UUID, update: BudgetUpdate
    ) -> WorkspaceBudget:
        async with self._lock:
            current = self._budgets.get(
                workspace_id, WorkspaceBudget(workspace_id=workspace_id)
            )
            updated_fields: dict[str, Any] = {}
            # Only set keys that the caller explicitly provided.
            data = update.model_dump(exclude_unset=True)
            for key, value in data.items():
                updated_fields[key] = value
            new_record = current.model_copy(update=updated_fields)
            # Sanity: hard limit must be >= daily limit when both set
            # (otherwise daily soft-cap is meaningless).
            if (
                new_record.daily_limit_usd is not None
                and new_record.hard_limit_usd is not None
                and new_record.daily_limit_usd > new_record.hard_limit_usd
            ):
                raise BudgetError(
                    "daily_limit_usd must be <= hard_limit_usd when both are set"
                )
            self._budgets[workspace_id] = new_record
            return new_record

    async def record_spend(
        self, workspace_id: UUID, amount_usd: Decimal
    ) -> WorkspaceBudget:
        """Increment both spent_today and spent_total. Called by the
        runtime after each successful turn."""
        if amount_usd < 0:
            raise BudgetError("amount_usd must be non-negative")
        async with self._lock:
            current = self._budgets.get(
                workspace_id, WorkspaceBudget(workspace_id=workspace_id)
            )
            updated = current.model_copy(
                update={
                    "spent_today_usd": current.spent_today_usd + amount_usd,
                    "spent_total_usd": current.spent_total_usd + amount_usd,
                }
            )
            self._budgets[workspace_id] = updated
            return updated


def serialise_budget(b: WorkspaceBudget) -> dict[str, Any]:
    return {
        "workspace_id": str(b.workspace_id),
        "daily_limit_usd": (
            str(b.daily_limit_usd) if b.daily_limit_usd is not None else None
        ),
        "hard_limit_usd": (
            str(b.hard_limit_usd) if b.hard_limit_usd is not None else None
        ),
        "spent_today_usd": str(b.spent_today_usd),
        "spent_total_usd": str(b.spent_total_usd),
    }


__all__ = [
    "BudgetError",
    "BudgetService",
    "BudgetUpdate",
    "WorkspaceBudget",
    "serialise_budget",
]
