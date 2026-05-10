from __future__ import annotations

import asyncio
import secrets
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from loop_control_plane._app_agents import AgentRecord

WebChannelStatus = Literal["disabled", "enabled"]


class WebChannelRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    agent_id: UUID
    workspace_id: UUID
    status: WebChannelStatus
    channel_id: str | None
    token: str | None
    enabled_at: datetime | None


def disabled_web_channel(agent: AgentRecord) -> WebChannelRecord:
    return WebChannelRecord(
        agent_id=agent.id,
        workspace_id=agent.workspace_id,
        status="disabled",
        channel_id=None,
        token=None,
        enabled_at=None,
    )


def web_channel_payload(record: WebChannelRecord) -> dict[str, Any]:
    return {
        "agentId": str(record.agent_id),
        "status": record.status,
        "channelId": record.channel_id,
        "token": record.token,
        "enabledAt": record.enabled_at.isoformat() if record.enabled_at else None,
    }


def web_channel_audit_payload(record: WebChannelRecord) -> dict[str, Any]:
    return {
        "agent_id": str(record.agent_id),
        "status": record.status,
        "channel_id": record.channel_id,
        "enabled_at": record.enabled_at.isoformat() if record.enabled_at else None,
    }


class WebChannelRegistry:
    """Agent-scoped browser embed channel state.

    The web channel token is returned only through the web-channel route for
    snippet generation. Audit payloads and channel-binding metadata never carry
    the token itself.
    """

    def __init__(self) -> None:
        self._records: dict[UUID, WebChannelRecord] = {}
        self._lock = asyncio.Lock()

    async def get(self, *, agent: AgentRecord) -> WebChannelRecord:
        async with self._lock:
            return self._records.get(agent.id) or disabled_web_channel(agent)

    async def enable(self, *, agent: AgentRecord) -> WebChannelRecord:
        async with self._lock:
            previous = self._records.get(agent.id)
            record = WebChannelRecord(
                agent_id=agent.id,
                workspace_id=agent.workspace_id,
                status="enabled",
                channel_id=previous.channel_id
                if previous and previous.channel_id
                else f"wch_{secrets.token_urlsafe(9).replace('-', '').replace('_', '')[:12]}",
                token=f"wct_{secrets.token_urlsafe(24).replace('-', '').replace('_', '')}",
                enabled_at=datetime.now(UTC),
            )
            self._records[agent.id] = record
            return record

    async def disable(self, *, agent: AgentRecord) -> WebChannelRecord:
        async with self._lock:
            record = disabled_web_channel(agent)
            self._records[agent.id] = record
            return record


__all__ = [
    "WebChannelRecord",
    "WebChannelRegistry",
    "disabled_web_channel",
    "web_channel_audit_payload",
    "web_channel_payload",
]
