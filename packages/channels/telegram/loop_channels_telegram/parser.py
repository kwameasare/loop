"""Parse a Telegram Bot API ``update`` payload."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from loop_channels_core import InboundEvent, InboundEventKind


def parse_update(
    payload: dict[str, Any],
    *,
    workspace_id: UUID,
    agent_id: UUID,
    conversation_id: UUID,
) -> tuple[InboundEvent, int] | None:
    """Parse a Telegram update.

    Returns ``(event, chat_id)`` for actionable text messages,
    otherwise ``None`` (channel posts, edited messages, callback
    queries are deferred to S037b).
    """

    message = payload.get("message")
    if not isinstance(message, dict):
        return None

    chat = message.get("chat") or {}
    if not isinstance(chat, dict):
        return None
    chat_id = chat.get("id")
    if not isinstance(chat_id, int):
        return None

    text = message.get("text")
    if not isinstance(text, str) or not text:
        return None

    sender = message.get("from") or {}
    user_id = str(sender.get("id", "")) or None

    metadata: dict[str, str] = {"chat_id": str(chat_id)}
    if isinstance(sender.get("username"), str):
        metadata["username"] = str(sender["username"])
    if isinstance(message.get("message_id"), int):
        metadata["message_id"] = str(message["message_id"])

    event = InboundEvent(
        workspace_id=workspace_id,
        agent_id=agent_id,
        conversation_id=conversation_id,
        kind=InboundEventKind.MESSAGE,
        user_id=user_id,
        text=text,
        metadata=metadata,
    )
    return event, chat_id


__all__ = ["parse_update"]
