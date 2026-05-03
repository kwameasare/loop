from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request, Response

from loop_control_plane._app_agents import AgentCreate, agent_payload
from loop_control_plane._app_common import ACTIVE_WORKSPACE, CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import authorize_workspace_access

router = APIRouter(prefix="/v1/agents", tags=["Agents"])


async def _authorise(request: Request, *, workspace_id: UUID, caller_sub: str) -> None:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )


@router.post("", status_code=201)
async def create_agent(
    request: Request,
    body: AgentCreate,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    runtime = request.app.state.cp
    await _authorise(request, workspace_id=workspace_id, caller_sub=caller_sub)
    agent = await runtime.agents.create(workspace_id=workspace_id, body=body)
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="agent:create",
        resource_type="agent",
        store=runtime.audit_events,
        resource_id=str(agent.id),
        request_id=request_id(request),
        payload=body.model_dump(mode="json"),
    )
    return agent_payload(agent)


@router.get("")
async def list_agents(
    request: Request,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    await _authorise(request, workspace_id=workspace_id, caller_sub=caller_sub)
    agents = await request.app.state.cp.agents.list_for_workspace(workspace_id)
    return {"items": [agent_payload(agent) for agent in agents]}


@router.get("/{agent_id}")
async def get_agent(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    await _authorise(request, workspace_id=workspace_id, caller_sub=caller_sub)
    agent = await request.app.state.cp.agents.get(workspace_id=workspace_id, agent_id=agent_id)
    return agent_payload(agent)


@router.delete("/{agent_id}", status_code=204)
async def archive_agent(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> Response:
    await _authorise(request, workspace_id=workspace_id, caller_sub=caller_sub)
    await request.app.state.cp.agents.archive(workspace_id=workspace_id, agent_id=agent_id)
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="agent:delete",
        resource_type="agent",
        store=request.app.state.cp.audit_events,
        resource_id=str(agent_id),
        request_id=request_id(request),
    )
    return Response(status_code=204)
