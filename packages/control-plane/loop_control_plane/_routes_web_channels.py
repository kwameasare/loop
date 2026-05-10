from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.channel_bindings import (
    ChannelBindingUpsert,
    ChannelReadinessUpdate,
)
from loop_control_plane.web_channels import (
    WebChannelRecord,
    web_channel_audit_payload,
    web_channel_payload,
)

router = APIRouter(prefix="/v1/agents", tags=["WebChannels"])


async def _agent_for_caller(
    cp: Any,
    *,
    agent_id: UUID,
    caller_sub: str,
    required_role: Role | None = None,
) -> Any:
    workspaces = await cp.workspaces.list_for_user(caller_sub)
    for workspace in workspaces:
        for agent in await cp.agents.list_for_workspace(workspace.id):
            if agent.id != agent_id:
                continue
            await authorize_workspace_access(
                workspaces=cp.workspaces,
                workspace_id=agent.workspace_id,
                user_sub=caller_sub,
                required_role=required_role,
            )
            return agent
    raise HTTPException(status_code=404, detail="unknown agent")


def _audit(
    request: Request,
    *,
    workspace_id: UUID,
    caller_sub: str,
    action: str,
    record: WebChannelRecord,
) -> None:
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action=action,
        resource_type="web_channel",
        resource_id=record.channel_id or str(record.agent_id),
        store=request.app.state.cp.audit_events,
        request_id=request_id(request),
        payload=web_channel_audit_payload(record),
    )


async def _mark_web_binding_enabled(
    request: Request,
    *,
    agent: Any,
    record: WebChannelRecord,
) -> None:
    cp = request.app.state.cp
    binding = await cp.channel_bindings.upsert(
        agent=agent,
        body=ChannelBindingUpsert(
            channel_type="web_chat",
            provider="Loop Web",
            display_name="Web chat",
            status="draft",
            identity_config={"embed": "browser", "token_scope": "web_channel"},
            auth_config_ref=f"web-channel/{record.channel_id}",
        ),
    )
    await cp.channel_bindings.set_readiness(
        agent=agent,
        binding_id=binding.id,
        check_id="snippet_minted",
        body=ChannelReadinessUpdate(
            status="passed",
            evidence_ref=f"web-channel/{record.channel_id}/snippet",
            message="Embed token minted by cp-api.",
        ),
    )


async def _mark_web_binding_disabled(
    request: Request,
    *,
    agent: Any,
) -> None:
    await request.app.state.cp.channel_bindings.upsert(
        agent=agent,
        body=ChannelBindingUpsert(
            channel_type="web_chat",
            provider="Loop Web",
            display_name="Web chat",
            status="paused",
            identity_config={},
            auth_config_ref=None,
        ),
    )


@router.get("/{agent_id}/channels/web")
async def get_web_channel(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    agent = await _agent_for_caller(
        cp,
        agent_id=agent_id,
        caller_sub=caller_sub,
    )
    record = await cp.web_channels.get(agent=agent)
    return web_channel_payload(record)


@router.post("/{agent_id}/channels/web/enable")
async def enable_web_channel(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    agent = await _agent_for_caller(
        cp,
        agent_id=agent_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    record = await cp.web_channels.enable(agent=agent)
    await _mark_web_binding_enabled(request, agent=agent, record=record)
    _audit(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
        action="web_channel:enable",
        record=record,
    )
    return web_channel_payload(record)


@router.post("/{agent_id}/channels/web/disable")
async def disable_web_channel(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    agent = await _agent_for_caller(
        cp,
        agent_id=agent_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    record = await cp.web_channels.disable(agent=agent)
    await _mark_web_binding_disabled(request, agent=agent)
    _audit(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
        action="web_channel:disable",
        record=record,
    )
    return web_channel_payload(record)


__all__ = ["router"]
