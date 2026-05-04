"""Workspace routes for the cp-api app."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, Request

from loop_control_plane._app_common import CALLER, JSON_BODY, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.workspaces import WorkspaceError

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


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
    x_loop_region: str | None = Header(default=None, alias="X-Loop-Region"),
) -> None:
    """Delete a workspace. OWNER-only.

    For GDPR Art-17 hard-erasure of tenant data (members, api_keys,
    agent rows, conversations, secrets, KB docs), enqueue a separate
    request via ``POST /v1/workspaces/{id}/data-deletion`` (P0.8b).
    This endpoint removes the *workspace registration* — once the row
    is gone the routes return 404 and no new turns can be billed
    against it. The DSR worker handles the cascading data purge
    asynchronously.

    Idempotency: deleting an already-deleted workspace returns 404
    rather than 204 (preserves the "deleted" state report).
    """
    runtime = request.app.state.cp
    # Service-layer `delete` enforces owner-only; we still call
    # `authorize_workspace_access` first so the caller gets a clean
    # 401/403 envelope before the service-layer error path triggers.
    from loop_control_plane.authorize import Role, authorize_workspace_access

    await authorize_workspace_access(
        workspaces=runtime.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.OWNER,
    )
    if x_loop_region is not None:
        ws = await runtime.workspaces.get(workspace_id)
        if ws.region != x_loop_region:
            raise WorkspaceError("X-Loop-Region must match workspace region")
    await runtime.workspaces.delete(
        workspace_id=workspace_id, actor_sub=caller_sub
    )
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="workspace:delete",
        resource_type="workspace",
        store=runtime.audit_events,
        resource_id=str(workspace_id),
        request_id=request_id(request),
        # Body is empty for DELETE; record the action only.
        payload={"workspace_id": str(workspace_id)},
    )
    # 204 No Content


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


# --------------------------------------------------------------------------- #
# Member CRUD (P0.4)                                                          #
# --------------------------------------------------------------------------- #
#
# WorkspaceAPI already implements the full lifecycle (list_members,
# add_member, remove_member, update_member_role); only the FastAPI
# shim was missing. Each mutating route emits an audit event so SOC2
# CC6.5 / CC7.3 evidence is concrete (P0.7a).


@router.get("/{workspace_id}/members")
async def list_workspace_members(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
    x_loop_region: str | None = Header(default=None, alias="X-Loop-Region"),
) -> dict[str, Any]:
    """List all members of a workspace. Any member can read."""
    return await request.app.state.cp.workspace_api.list_members(
        caller_sub=caller_sub,
        workspace_id=workspace_id,
        request_region=x_loop_region,
    )


@router.post("/{workspace_id}/members", status_code=201)
async def add_workspace_member(
    request: Request,
    workspace_id: UUID,
    body: dict[str, Any] = JSON_BODY,
    caller_sub: str = CALLER,
    x_loop_region: str | None = Header(default=None, alias="X-Loop-Region"),
) -> dict[str, Any]:
    """Add a user to the workspace. Owner-only.

    Body shape: ``{"user_sub": "<idp-mapped uuid>", "role": "MEMBER" | "ADMIN" | "OWNER" | "VIEWER"}``.
    """
    runtime = request.app.state.cp
    membership = await runtime.workspace_api.add_member(
        caller_sub=caller_sub,
        workspace_id=workspace_id,
        body=body,
        request_region=x_loop_region,
    )
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="workspace:member:add",
        resource_type="workspace_member",
        store=runtime.audit_events,
        resource_id=str(membership.get("user_sub", "")),
        request_id=request_id(request),
        # Don't log the body verbatim — it may contain emails / PII; we
        # capture user_sub + role explicitly so audit rows stay
        # diff-able without storing more than necessary.
        payload={"user_sub": membership.get("user_sub"), "role": membership.get("role")},
    )
    return membership


@router.delete("/{workspace_id}/members/{user_sub}", status_code=204)
async def remove_workspace_member(
    request: Request,
    workspace_id: UUID,
    user_sub: str,
    caller_sub: str = CALLER,
    x_loop_region: str | None = Header(default=None, alias="X-Loop-Region"),
) -> None:
    """Remove a member from the workspace. Owner-only."""
    runtime = request.app.state.cp
    await runtime.workspace_api.remove_member(
        caller_sub=caller_sub,
        workspace_id=workspace_id,
        user_sub=user_sub,
        request_region=x_loop_region,
    )
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="workspace:member:remove",
        resource_type="workspace_member",
        store=runtime.audit_events,
        resource_id=user_sub,
        request_id=request_id(request),
        payload={"user_sub": user_sub},
    )
    # 204 No Content


@router.patch("/{workspace_id}/members/{user_sub}")
async def update_workspace_member_role(
    request: Request,
    workspace_id: UUID,
    user_sub: str,
    body: dict[str, Any] = JSON_BODY,
    caller_sub: str = CALLER,
    x_loop_region: str | None = Header(default=None, alias="X-Loop-Region"),
) -> dict[str, Any]:
    """Change a member's role. Owner-only.

    Body shape: ``{"role": "MEMBER" | "ADMIN" | "OWNER" | "VIEWER"}``.
    """
    runtime = request.app.state.cp
    membership = await runtime.workspace_api.update_member_role(
        caller_sub=caller_sub,
        workspace_id=workspace_id,
        user_sub=user_sub,
        body=body,
        request_region=x_loop_region,
    )
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="workspace:member:role_change",
        resource_type="workspace_member",
        store=runtime.audit_events,
        resource_id=user_sub,
        request_id=request_id(request),
        payload={"user_sub": user_sub, "role": membership.get("role")},
    )
    return membership
