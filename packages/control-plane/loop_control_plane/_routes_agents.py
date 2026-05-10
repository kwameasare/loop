from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response

from loop_control_plane._app_agents import AgentCreate, agent_payload
from loop_control_plane._app_common import ACTIVE_WORKSPACE, CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import authorize_workspace_access

router = APIRouter(prefix="/v1/agents", tags=["Agents"])

AgentObjectState = Literal[
    "draft",
    "saved",
    "staged",
    "canary",
    "production",
    "rolled_back",
    "archived",
]


async def _authorise(request: Request, *, workspace_id: UUID, caller_sub: str) -> None:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )


async def _agent_by_id(request: Request, *, agent_id: UUID, caller_sub: str) -> Any:
    cp = request.app.state.cp
    agent = cp.agents._agents.get(agent_id)  # type: ignore[attr-defined]
    if agent is None:
        raise HTTPException(status_code=404, detail="unknown agent")
    await _authorise(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
    )
    return agent


async def _agent_payload_with_state(request: Request, agent: Any) -> dict[str, Any]:
    payload = agent_payload(agent)
    payload.update(await _derive_agent_state(request, agent))
    return payload


async def _derive_agent_state(request: Request, agent: Any) -> dict[str, str]:
    if agent.archived_at is not None:
        return {
            "object_state": "archived",
            "state_reason": "Agent is archived.",
            "state_evidence_ref": f"agent/{agent.id}/archive",
        }

    deployments = await request.app.state.cp.deployments.list_for_agent(agent=agent)
    if deployments:
        latest_deployment = deployments[0]
        if latest_deployment.status == "live":
            return {
                "object_state": "production",
                "state_reason": f"Deployment {latest_deployment.id} is live.",
                "state_evidence_ref": f"deployment/{latest_deployment.id}",
            }
        if latest_deployment.status in {"canary", "ramp", "paused"}:
            return {
                "object_state": "canary",
                "state_reason": (
                    f"Deployment {latest_deployment.id} is in {latest_deployment.status} rollout."
                ),
                "state_evidence_ref": f"deployment/{latest_deployment.id}",
            }
        if latest_deployment.status == "shadow":
            return {
                "object_state": "staged",
                "state_reason": f"Deployment {latest_deployment.id} is shadowing traffic.",
                "state_evidence_ref": f"deployment/{latest_deployment.id}",
            }
        if latest_deployment.status == "rolled_back":
            return {
                "object_state": "rolled_back",
                "state_reason": f"Deployment {latest_deployment.id} was rolled back.",
                "state_evidence_ref": f"deployment/{latest_deployment.id}",
            }

    current_package = await request.app.state.cp.change_packages.current(agent=agent)
    if current_package is not None:
        if current_package.status in {"submitted", "approved", "deployable"}:
            return {
                "object_state": "staged",
                "state_reason": f"Change Package {current_package.id} is in review.",
                "state_evidence_ref": f"change_package/{current_package.id}",
            }
        if current_package.status == "generated":
            return {
                "object_state": "saved",
                "state_reason": f"Change Package {current_package.id} was generated.",
                "state_evidence_ref": f"change_package/{current_package.id}",
            }

    commitment = await request.app.state.cp.agent_commitments.current(agent=agent)
    if commitment.status == "accepted":
        return {
            "object_state": "saved",
            "state_reason": f"Commitment Document {commitment.id} is accepted.",
            "state_evidence_ref": f"commitment/{commitment.id}",
        }
    return {
        "object_state": "draft",
        "state_reason": "Commitment Document is still draft.",
        "state_evidence_ref": f"commitment/{commitment.id}",
    }


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
    await runtime.agent_commitments.ensure_current(agent=agent, created_from="agent:create")
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
    return await _agent_payload_with_state(request, agent)


@router.get("")
async def list_agents(
    request: Request,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    await _authorise(request, workspace_id=workspace_id, caller_sub=caller_sub)
    agents = await request.app.state.cp.agents.list_for_workspace(workspace_id)
    return {"items": [await _agent_payload_with_state(request, agent) for agent in agents]}


@router.get("/{agent_id}")
async def get_agent(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    agent = await _agent_by_id(request, agent_id=agent_id, caller_sub=caller_sub)
    return await _agent_payload_with_state(request, agent)


@router.delete("/{agent_id}", status_code=204)
async def archive_agent(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
) -> Response:
    agent = await _agent_by_id(request, agent_id=agent_id, caller_sub=caller_sub)
    await request.app.state.cp.agents.archive(
        workspace_id=agent.workspace_id,
        agent_id=agent_id,
    )
    record_audit_event(
        workspace_id=agent.workspace_id,
        actor_sub=caller_sub,
        action="agent:delete",
        resource_type="agent",
        store=request.app.state.cp.audit_events,
        resource_id=str(agent_id),
        request_id=request_id(request),
    )
    return Response(status_code=204)
