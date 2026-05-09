from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request

from loop_control_plane._app_common import ACTIVE_WORKSPACE, CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import authorize_workspace_access
from loop_control_plane.channel_bindings import (
    ChannelBindingUpsert,
    ChannelReadinessUpdate,
    channel_binding_payload,
)

router = APIRouter(prefix="/v1/agents", tags=["ChannelBindings"])


async def _agent(
    request: Request,
    *,
    agent_id: UUID,
    workspace_id: UUID,
    caller_sub: str,
) -> Any:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    return await request.app.state.cp.agents.get(
        workspace_id=workspace_id,
        agent_id=agent_id,
    )


def _audit(
    request: Request,
    *,
    workspace_id: UUID,
    caller_sub: str,
    action: str,
    resource_id: str,
    payload: object | None = None,
) -> None:
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action=action,
        resource_type="channel_binding",
        resource_id=resource_id,
        store=request.app.state.cp.audit_events,
        request_id=request_id(request),
        payload=payload,
    )


@router.get("/{agent_id}/channel-bindings")
async def list_channel_bindings(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
    )
    bindings = await request.app.state.cp.channel_bindings.list_for_agent(agent=agent)
    return {"items": [channel_binding_payload(binding) for binding in bindings]}


@router.post("/{agent_id}/channel-bindings", status_code=201)
async def upsert_channel_binding(
    request: Request,
    agent_id: UUID,
    body: ChannelBindingUpsert,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
    )
    binding = await request.app.state.cp.channel_bindings.upsert(
        agent=agent,
        body=body,
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="channel_binding:upsert",
        resource_id=binding.id,
        payload={
            "agent_id": str(agent_id),
            "channel_type": binding.channel_type,
            "status": binding.status,
        },
    )
    return channel_binding_payload(binding)


@router.post("/{agent_id}/channel-bindings/{binding_id}/readiness/{check_id}")
async def update_channel_readiness(
    request: Request,
    agent_id: UUID,
    binding_id: str,
    check_id: str,
    body: ChannelReadinessUpdate,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
    )
    binding = await request.app.state.cp.channel_bindings.set_readiness(
        agent=agent,
        binding_id=binding_id,
        check_id=check_id,
        body=body,
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="channel_binding:readiness",
        resource_id=binding.id,
        payload={
            "agent_id": str(agent_id),
            "channel_type": binding.channel_type,
            "check_id": check_id,
            "status": body.status,
        },
    )
    return channel_binding_payload(binding)
