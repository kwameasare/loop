from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, Request

from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.workspaces import WorkspaceError


async def resolve_agent_for_route(
    request: Request,
    *,
    agent_id: UUID,
    caller_sub: str,
    workspace_id: UUID | None = None,
    required_role: Role | None = None,
) -> Any:
    """Resolve an agent-scoped route without assuming in-memory agent storage."""

    cp = request.app.state.cp
    try:
        if workspace_id is None:
            agent = await cp.agents.get_by_id(agent_id=agent_id)
            workspace_id = agent.workspace_id
        else:
            agent = await cp.agents.get(workspace_id=workspace_id, agent_id=agent_id)
    except WorkspaceError as exc:
        raise HTTPException(status_code=404, detail="unknown agent") from exc

    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=required_role,
    )
    return agent
