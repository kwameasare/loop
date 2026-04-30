"""Parse a Bot Framework activity payload (Teams variant)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from loop_channels_core import InboundEvent, InboundEventKind


def parse_activity(
    payload: dict[str, Any],
    *,
    workspace_id: UUID,
    agent_id: UUID,
    conversation_id: UUID,
) -> tuple[InboundEvent, str] | None:
    """Parse a Teams activity.

    Returns ``(event, conversation_ref_id)`` for ``message`` activities
    only -- ``conversationUpdate`` (member added etc.) and
    ``invoke`` activities are deferred. ``conversation_ref_id`` is the
    Bot Framework conversation id, needed to route the reply.
    """
    if payload.get("type") != "message":
        return None

    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        return None

    conversation = payload.get("conversation") or {}
    if not isinstance(conversation, dict):
        return None
    convo_ref = conversation.get("id")
    if not isinstance(convo_ref, str) or not convo_ref:
        return None

    sender = payload.get("from") or {}
    user_id = (
        str(sender.get("id"))
        if isinstance(sender, dict) and sender.get("id") is not None
        else None
    )

    metadata: dict[str, str] = {"conversation_ref": convo_ref}
    service_url = payload.get("serviceUrl")
    if isinstance(service_url, str):
        metadata["service_url"] = service_url
    activity_id = payload.get("id")
    if isinstance(activity_id, str):
        metadata["activity_id"] = activity_id
    channel_id_raw = payload.get("channelId")
    if isinstance(channel_id_raw, str):
        metadata["bot_channel"] = channel_id_raw

    event = InboundEvent(
        workspace_id=workspace_id,
        agent_id=agent_id,
        conversation_id=conversation_id,
        kind=InboundEventKind.MESSAGE,
        user_id=user_id,
        text=text,
        metadata=metadata,
    )
    return event, convo_ref


__all__ = ["parse_activity"]
