"""Per-channel-binding BYOC credentials routes.

Enterprise admins paste their Twilio / Meta / Slack / Discord / etc.
credentials in the studio's channel-binding form. cp encrypts them at
rest. The studio can confirm a value exists + when it was rotated but
never reads the plaintext back.

Endpoints (keyed by ``agent_id`` + ``channel_type`` since the existing
binding registry stores at most one binding per channel per agent):

    GET    /v1/agents/{agent_id}/channels/{channel_type}/credentials
           — status: ``{has_value, provider, created_at, rotated_at}``.

    PUT    /v1/agents/{agent_id}/channels/{channel_type}/credentials
           — upload / rotate. Body: ``{provider, values}``.

    DELETE /v1/agents/{agent_id}/channels/{channel_type}/credentials
           — wipe.

The runtime resolves an agent's plaintext credentials at send time via
``cp.byoc_secrets.reveal_for_adapter(agent_id=..., channel_type=...)``.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access

router = APIRouter(prefix="/v1/agents", tags=["BYOCCredentials"])

# Channel types cp accepts on this route. Mirrors the keys in the
# binding registry; new channels add themselves here.
_KNOWN_CHANNELS = {
    "web_chat",
    "whatsapp",
    "telegram",
    "slack",
    "teams",
    "sms",
    "email",
    "voice",
    "webhook_api",
    "rcs",
    "discord",
}


class BYOCCredentialsPut(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    provider: str = Field(min_length=1, max_length=64)
    """Free-form provider key (e.g. ``twilio``, ``meta_whatsapp``).
    cp does not interpret the shape of ``values`` — the channel
    adapter knows what fields its provider needs."""
    values: dict[str, Any]


async def _resolve_agent_workspace(
    request: Request, agent_id: UUID
) -> UUID:
    cp = request.app.state.cp
    agent = cp.agents._agents.get(agent_id)  # type: ignore[attr-defined]
    if agent is None:
        raise HTTPException(status_code=404, detail="unknown agent")
    return agent.workspace_id


def _validate_channel_type(channel_type: str) -> str:
    normalised = channel_type.lower().strip()
    if normalised not in _KNOWN_CHANNELS:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported channel_type: {channel_type}",
        )
    return normalised


@router.get("/{agent_id}/channels/{channel_type}/credentials")
async def get_credentials_status(
    request: Request,
    agent_id: UUID,
    channel_type: str,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    channel = _validate_channel_type(channel_type)
    workspace_id = await _resolve_agent_workspace(request, agent_id)
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    status = await cp.byoc_secrets.status(
        agent_id=agent_id, channel_type=channel
    )
    if status is None:
        return {
            "agent_id": str(agent_id),
            "channel_type": channel,
            "has_value": False,
        }
    return status


@router.put(
    "/{agent_id}/channels/{channel_type}/credentials", status_code=200
)
async def put_credentials(
    request: Request,
    agent_id: UUID,
    channel_type: str,
    body: BYOCCredentialsPut,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    channel = _validate_channel_type(channel_type)
    workspace_id = await _resolve_agent_workspace(request, agent_id)
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    record = await cp.byoc_secrets.put(
        workspace_id=workspace_id,
        agent_id=agent_id,
        channel_type=channel,
        provider=body.provider,
        values=body.values,
    )
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="byoc_credentials:put",
        resource_type="channel_binding",
        store=cp.audit_events,
        resource_id=f"{agent_id}:{channel}",
        request_id=request_id(request),
        payload={
            "provider": record.provider,
            "rotated": record.rotated_at is not None,
        },
    )
    return {
        "agent_id": str(agent_id),
        "workspace_id": str(workspace_id),
        "channel_type": channel,
        "provider": record.provider,
        "created_at": record.created_at.isoformat(),
        "rotated_at": (
            record.rotated_at.isoformat() if record.rotated_at else None
        ),
        "has_value": True,
    }


@router.delete(
    "/{agent_id}/channels/{channel_type}/credentials", status_code=204
)
async def delete_credentials(
    request: Request,
    agent_id: UUID,
    channel_type: str,
    caller_sub: str = CALLER,
) -> None:
    cp = request.app.state.cp
    channel = _validate_channel_type(channel_type)
    workspace_id = await _resolve_agent_workspace(request, agent_id)
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    await cp.byoc_secrets.delete(agent_id=agent_id, channel_type=channel)
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="byoc_credentials:delete",
        resource_type="channel_binding",
        store=cp.audit_events,
        resource_id=f"{agent_id}:{channel}",
        request_id=request_id(request),
        payload={},
    )
