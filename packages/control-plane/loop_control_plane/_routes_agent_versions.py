"""Agent version routes (P0.4).

* ``GET   /v1/agents/{agent_id}/versions`` — list (any member).
* ``POST  /v1/agents/{agent_id}/versions`` — create new version (ADMIN).
* ``POST  /v1/agents/{agent_id}/versions/{version_id}/promote`` —
  set as active (ADMIN). Idempotent.

Authorisation: routes route through `WorkspaceAPI`'s membership
check via the agent's workspace_id (which we resolve from the agent
itself).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.agent_versions import (
    AgentVersionCreate,
    AgentVersionError,
    _serialise_agent,
    _serialise_version,
)
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.workspaces import WorkspaceError

router = APIRouter(prefix="/v1/agents", tags=["AgentVersions"])


async def _agent_workspace(request: Request, agent_id: UUID) -> UUID:
    """Find the agent's workspace_id without enforcing membership;
    callers chain into `authorize_workspace_access` afterwards."""
    cp = request.app.state.cp
    # AgentRegistry.get requires (workspace_id, agent_id); to look up
    # cross-workspace we walk the in-memory map. Postgres impl does
    # `SELECT workspace_id FROM agents WHERE id = $1`.
    agent = cp.agents._agents.get(agent_id)  # type: ignore[attr-defined]
    if agent is None:
        raise HTTPException(status_code=404, detail="unknown agent")
    return agent.workspace_id


@router.get("/{agent_id}/versions")
async def list_versions(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    workspace_id = await _agent_workspace(request, agent_id)
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    rows = await cp.agent_versions.list_for_agent(
        workspace_id=workspace_id, agent_id=agent_id
    )
    return {"items": [_serialise_version(v) for v in rows]}


@router.post("/{agent_id}/versions", status_code=201)
async def create_version(
    request: Request,
    agent_id: UUID,
    body: AgentVersionCreate,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    """Create a new immutable version. ADMIN-only."""
    cp = request.app.state.cp
    workspace_id = await _agent_workspace(request, agent_id)
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    try:
        version = await cp.agent_versions.create(
            workspace_id=workspace_id,
            agent_id=agent_id,
            body=body,
            actor_sub=caller_sub,
        )
    except (AgentVersionError, WorkspaceError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="agent:version:create",
        resource_type="agent_version",
        store=cp.audit_events,
        resource_id=str(version.id),
        request_id=request_id(request),
        payload={
            "agent_id": str(agent_id),
            "version": version.version,
            "id": str(version.id),
        },
    )
    return _serialise_version(version)


@router.post("/{agent_id}/versions/{version_id}/promote", status_code=200)
async def promote_version(
    request: Request,
    agent_id: UUID,
    version_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    """Promote a version to active. ADMIN-only. Idempotent."""
    cp = request.app.state.cp
    workspace_id = await _agent_workspace(request, agent_id)
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    try:
        agent = await cp.agent_versions.promote(
            workspace_id=workspace_id,
            agent_id=agent_id,
            version_id=version_id,
            actor_sub=caller_sub,
        )
    except AgentVersionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="agent:version:promote",
        resource_type="agent_version",
        store=cp.audit_events,
        resource_id=str(version_id),
        request_id=request_id(request),
        payload={
            "agent_id": str(agent_id),
            "version_id": str(version_id),
            "active_version": agent.active_version,
        },
    )
    return _serialise_agent(agent)


__all__ = ["router"]
