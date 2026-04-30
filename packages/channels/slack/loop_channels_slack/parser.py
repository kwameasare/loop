"""Lift Slack JSON payloads into ``InboundEvent``s."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from loop_channels_core import InboundEvent, InboundEventKind


def parse_event(
    payload: dict[str, Any],
    *,
    workspace_id: UUID,
    agent_id: UUID,
    conversation_id: UUID,
) -> InboundEvent | None:
    """Parse a Slack Events API payload.

    Returns ``None`` for event types we don't care about. Returns a
    fresh `InboundEvent` for ``message`` and ``app_mention`` events.
    """
    if payload.get("type") != "event_callback":
        return None
    event = payload.get("event", {})
    if not isinstance(event, dict):
        return None
    et = event.get("type")
    if et not in ("message", "app_mention"):
        return None
    # Filter bot-authored echoes.
    if event.get("bot_id") or event.get("subtype") == "bot_message":
        return None
    text = str(event.get("text", ""))
    return InboundEvent(
        workspace_id=workspace_id,
        agent_id=agent_id,
        conversation_id=conversation_id,
        kind=InboundEventKind.MESSAGE,
        user_id=event.get("user"),
        text=text,
        metadata={
            "slack_channel": str(event.get("channel", "")),
            "slack_thread_ts": str(event.get("thread_ts") or event.get("ts", "")),
            "slack_event_type": et,
        },
    )


def parse_command(
    payload: dict[str, str],
    *,
    workspace_id: UUID,
    agent_id: UUID,
    conversation_id: UUID,
) -> InboundEvent:
    """Parse a Slack slash-command form payload."""
    return InboundEvent(
        workspace_id=workspace_id,
        agent_id=agent_id,
        conversation_id=conversation_id,
        kind=InboundEventKind.MESSAGE,
        user_id=payload.get("user_id"),
        text=payload.get("text", ""),
        metadata={
            "slack_channel": payload.get("channel_id", ""),
            "slack_command": payload.get("command", ""),
            "slack_response_url": payload.get("response_url", ""),
        },
    )


__all__ = ["parse_command", "parse_event"]
