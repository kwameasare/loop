"""Workspace routes for the cp-api app."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, Request

from loop_control_plane._app_common import CALLER, JSON_BODY, request_id
from loop_control_plane.audit_events import record_audit_event

router = APIRouter(prefix="/v1/workspaces", tags=["Workspaces"])


@router.post("", status_code=201)
async def create_workspace(
    request: Request,
    body: dict[str, Any] = JSON_BODY,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    runtime = request.app.state.cp
    workspace = await runtime.workspace_api.create(caller_sub=caller_sub, body=body)
    record_audit_event(
        workspace_id=UUID(str(workspace["id"])),
        actor_sub=caller_sub,
        action="workspace:create",
        resource_type="workspace",
        store=runtime.audit_events,
        resource_id=str(workspace["id"]),
        request_id=request_id(request),
        payload=body,
    )
    return workspace


@router.get("")
async def list_workspaces(
    request: Request,
    caller_sub: str = CALLER,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    return await request.app.state.cp.workspace_api.list_for_caller(
        caller_sub=caller_sub, page=page, page_size=page_size
    )


@router.get("/{workspace_id}")
async def get_workspace(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
    x_loop_region: str | None = Header(default=None, alias="X-Loop-Region"),
) -> dict[str, Any]:
    return await request.app.state.cp.workspace_api.get(
        caller_sub=caller_sub,
        workspace_id=workspace_id,
        request_region=x_loop_region,
    )


@router.patch("/{workspace_id}")
async def patch_workspace(
    request: Request,
    workspace_id: UUID,
    body: dict[str, Any] = JSON_BODY,
    caller_sub: str = CALLER,
    x_loop_region: str | None = Header(default=None, alias="X-Loop-Region"),
) -> dict[str, Any]:
    runtime = request.app.state.cp
    workspace = await runtime.workspace_api.patch(
        caller_sub=caller_sub,
        workspace_id=workspace_id,
        body=body,
        request_region=x_loop_region,
    )
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="workspace:update",
        resource_type="workspace",
        store=runtime.audit_events,
        resource_id=str(workspace_id),
        request_id=request_id(request),
        payload=body,
    )
    return workspace
