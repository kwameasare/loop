"""Audit read routes for the cp-api app."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request

from loop_control_plane._app_audit import audit_payload
from loop_control_plane._app_common import CALLER
from loop_control_plane.authorize import authorize_workspace_access
from loop_control_plane.workspaces import WorkspaceError

router = APIRouter(tags=["Audit"])


@router.get("/v1/audit/events")
@router.get("/v1/audit-events")
async def list_audit_events(
    request: Request,
    workspace_id: UUID,
    limit: int = 100,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    if not 1 <= limit <= 1000:
        raise WorkspaceError("limit must be 1..1000")
    runtime = request.app.state.cp
    await authorize_workspace_access(
        workspaces=runtime.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    events = list(runtime.audit_events.list_for_workspace(workspace_id))
    return {"items": [audit_payload(e) for e in events[-limit:]], "total": len(events)}
