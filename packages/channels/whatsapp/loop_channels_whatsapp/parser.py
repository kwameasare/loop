"""Lift WhatsApp Cloud API webhook payloads into ``InboundEvent``s.

Cloud API delivers ``entry[].changes[].value.messages[]`` lists with
a single inbound user message most of the time. We surface
``messages[0]`` (the rest are stored as part of metadata) and ignore
``statuses`` callbacks (delivery receipts) since they don't drive
turns.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from loop_channels_core import InboundEvent, InboundEventKind

_TEXT_TYPES: frozenset[str] = frozenset({"text"})
_MEDIA_TYPES: frozenset[str] = frozenset({"image", "audio", "video", "document"})
_SUPPORTED_TYPES: frozenset[str] = _TEXT_TYPES | _MEDIA_TYPES


def parse_event(
    payload: dict[str, Any],
    *,
    workspace_id: UUID,
    agent_id: UUID,
    conversation_id: UUID,
) -> InboundEvent | None:
    """Parse a Cloud API webhook payload.

    Returns ``None`` when the payload contains only delivery
    statuses, has no ``messages`` array, or carries an unsupported
    message type. The first supported message in the payload becomes
    the inbound event; ``metadata`` carries the surface-native ids
    needed to reply.
    """
    if payload.get("object") != "whatsapp_business_account":
        return None
    entries = payload.get("entry") or []
    if not isinstance(entries, list):
        return None
    for entry in entries:
        for change in entry.get("changes", []) or []:
            value = change.get("value") or {}
            messages = value.get("messages") or []
            if not isinstance(messages, list) or not messages:
                continue
            phone_number_id = str(value.get("metadata", {}).get("phone_number_id", ""))
            for message in messages:
                if not isinstance(message, dict):
                    continue
                mtype = message.get("type")
                if mtype not in _SUPPORTED_TYPES:
                    continue
                text = ""
                media_id = ""
                if mtype == "text":
                    text = str(message.get("text", {}).get("body", ""))
                else:
                    media_id = str(message.get(mtype, {}).get("id", ""))
                    caption = message.get(mtype, {}).get("caption")
                    if isinstance(caption, str):
                        text = caption
                return InboundEvent(
                    workspace_id=workspace_id,
                    agent_id=agent_id,
                    conversation_id=conversation_id,
                    kind=InboundEventKind.MESSAGE,
                    user_id=str(message.get("from", "")),
                    text=text,
                    metadata={
                        "wa_message_id": str(message.get("id", "")),
                        "wa_phone_number_id": phone_number_id,
                        "wa_message_type": mtype,
                        "wa_media_id": media_id,
                    },
                )
    return None


__all__ = ["parse_event"]
