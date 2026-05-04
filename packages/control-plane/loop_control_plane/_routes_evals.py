"""Workspace eval suite + run routes (P0.4).

* ``GET   /v1/workspaces/{id}/eval-suites`` (any member)
* ``POST  /v1/workspaces/{id}/eval-suites`` (ADMIN)
* ``GET   /v1/eval-suites/{id}/runs``       (any member)
* ``POST  /v1/eval-suites/{id}/runs``       (ADMIN)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.eval_suites import (
    EvalError,
    EvalRunStart,
    EvalSuiteCreate,
    serialise_run,
    serialise_suite,
)

router_workspaces = APIRouter(prefix="/v1/workspaces", tags=["Evals"])
router_suites = APIRouter(prefix="/v1/eval-suites", tags=["Evals"])


@router_workspaces.get("/{workspace_id}/eval-suites")
async def list_suites(
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
    rows = await cp.eval_suites.list_suites(workspace_id)
    return {"items": [serialise_suite(s) for s in rows]}


@router_workspaces.post("/{workspace_id}/eval-suites", status_code=201)
async def create_suite(
    request: Request,
    workspace_id: UUID,
    body: EvalSuiteCreate,
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
        suite = await cp.eval_suites.create_suite(
            workspace_id=workspace_id, body=body, actor_sub=caller_sub
        )
    except EvalError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="eval:suite:create",
        resource_type="eval_suite",
        store=cp.audit_events,
        resource_id=str(suite.id),
        request_id=request_id(request),
        payload={
            "id": str(suite.id),
            "name": suite.name,
            "dataset_ref": suite.dataset_ref,
        },
    )
    return serialise_suite(suite)


async def _suite_workspace(request: Request, suite_id: UUID) -> UUID:
    cp = request.app.state.cp
    suite = cp.eval_suites._suites.get(suite_id)  # type: ignore[attr-defined]
    if suite is None:
        raise HTTPException(status_code=404, detail="unknown suite")
    return suite.workspace_id


@router_suites.get("/{suite_id}/runs")
async def list_runs(
    request: Request,
    suite_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    workspace_id = await _suite_workspace(request, suite_id)
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    try:
        rows = await cp.eval_suites.list_runs(
            workspace_id=workspace_id, suite_id=suite_id
        )
    except EvalError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"items": [serialise_run(r) for r in rows]}


@router_suites.post("/{suite_id}/runs", status_code=202)
async def start_run(
    request: Request,
    suite_id: UUID,
    body: EvalRunStart,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    """Kick off a new eval run. ADMIN-only."""
    cp = request.app.state.cp
    workspace_id = await _suite_workspace(request, suite_id)
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    try:
        run = await cp.eval_suites.start_run(
            workspace_id=workspace_id,
            suite_id=suite_id,
            actor_sub=caller_sub,
        )
    except EvalError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="eval:run:start",
        resource_type="eval_run",
        store=cp.audit_events,
        resource_id=str(run.id),
        request_id=request_id(request),
        payload={"id": str(run.id), "suite_id": str(suite_id), "note": body.note},
    )
    return serialise_run(run)


__all__ = ["router_suites", "router_workspaces"]
