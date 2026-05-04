"""Workspace budget routes (P0.4).

* ``GET   /v1/workspaces/{id}/budgets`` — any member can read
  (cost ops + observability).
* ``PATCH /v1/workspaces/{id}/budgets`` — ADMIN-only mutation,
  emits audit event.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.budgets import BudgetError, BudgetUpdate, serialise_budget

router = APIRouter(prefix="/v1/workspaces", tags=["Budgets"])


@router.get("/{workspace_id}/budgets")
async def get_budget(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    budget = await cp.budgets.get(workspace_id)
    return serialise_budget(budget)


@router.patch("/{workspace_id}/budgets")
async def patch_budget(
    request: Request,
    workspace_id: UUID,
    body: BudgetUpdate,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    try:
        budget = await cp.budgets.patch(workspace_id, body)
    except BudgetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="workspace:budget:update",
        resource_type="workspace_budget",
        store=cp.audit_events,
        resource_id=str(workspace_id),
        request_id=request_id(request),
        payload={
            "daily_limit_usd": (
                str(budget.daily_limit_usd)
                if budget.daily_limit_usd is not None
                else None
            ),
            "hard_limit_usd": (
                str(budget.hard_limit_usd)
                if budget.hard_limit_usd is not None
                else None
            ),
        },
    )
    return serialise_budget(budget)


__all__ = ["router"]
