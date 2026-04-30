"""Parse a Discord Interactions API payload."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from loop_channels_core import InboundEvent, InboundEventKind

PING = 1
APPLICATION_COMMAND = 2
MESSAGE_COMPONENT = 3


def _extract_text(payload: dict[str, Any]) -> str | None:
    interaction_type = payload.get("type")
    data = payload.get("data") or {}
    if interaction_type == APPLICATION_COMMAND:
        options = data.get("options")
        if isinstance(options, list):
            for opt in options:
                if not isinstance(opt, dict):
                    continue
                value = opt.get("value")
                if isinstance(value, str) and value.strip():
                    return value
        # No options -> use the command name itself as the prompt.
        name = data.get("name")
        if isinstance(name, str) and name.strip():
            return f"/{name}"
        return None
    if interaction_type == MESSAGE_COMPONENT:
        custom = data.get("custom_id")
        if isinstance(custom, str) and custom.strip():
            return custom
        return None
    return None


def parse_interaction(
    payload: dict[str, Any],
    *,
    workspace_id: UUID,
    agent_id: UUID,
    conversation_id: UUID,
) -> tuple[InboundEvent, str] | None:
    """Parse one interaction.

    Returns ``(event, channel_id)`` for actionable interactions.
    PING (``type == 1``) is the platform handshake and is handled by
    the host without a dispatcher round-trip, so this returns
    ``None`` for it.
    """
    if payload.get("type") == PING:
        return None

    channel_id = payload.get("channel_id")
    if not isinstance(channel_id, str) or not channel_id:
        return None

    text = _extract_text(payload)
    if text is None:
        return None

    member = payload.get("member") or {}
    user = (member.get("user") if isinstance(member, dict) else None) or payload.get("user") or {}
    user_id = str(user.get("id")) if isinstance(user, dict) and user.get("id") is not None else None

    metadata: dict[str, str] = {"channel_id": channel_id}
    if isinstance(payload.get("guild_id"), str):
        metadata["guild_id"] = str(payload["guild_id"])
    interaction_token = payload.get("token")
    if isinstance(interaction_token, str):
        metadata["interaction_token"] = interaction_token
    application_id = payload.get("application_id")
    if isinstance(application_id, str):
        metadata["application_id"] = application_id

    event = InboundEvent(
        workspace_id=workspace_id,
        agent_id=agent_id,
        conversation_id=conversation_id,
        kind=InboundEventKind.MESSAGE,
        user_id=user_id,
        text=text,
        metadata=metadata,
    )
    return event, channel_id


__all__ = ["APPLICATION_COMMAND", "MESSAGE_COMPONENT", "PING", "parse_interaction"]
