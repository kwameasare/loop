"""Translate OutboundFrames into Bot Framework reply activities."""

from __future__ import annotations

from typing import Any

from loop_channels_core import OutboundFrame, OutboundFrameKind


def to_reply_activity(
    frame: OutboundFrame,
    *,
    conversation_ref: str,
    reply_to_id: str | None = None,
) -> dict[str, Any] | None:
    """Map a :class:`OutboundFrame` to a reply Activity body.

    Streaming token frames are dropped: Teams accepts only the final
    rendered message. Returns ``None`` for frames that should not
    produce a Teams message.
    """
    if frame.kind in (OutboundFrameKind.AGENT_TOKEN, OutboundFrameKind.DONE):
        return None

    if frame.kind == OutboundFrameKind.AGENT_MESSAGE:
        text = frame.text or ""
    elif frame.kind == OutboundFrameKind.TOOL_CALL_START:
        tool = frame.payload.get("tool", "tool")
        text = f"_Calling {tool}\u2026_"
    elif frame.kind == OutboundFrameKind.TOOL_CALL_END:
        tool = frame.payload.get("tool", "tool")
        text = f"_Finished {tool}._"
    elif frame.kind == OutboundFrameKind.HANDOFF:
        target = frame.payload.get("to", "human")
        text = f"Handed off to **{target}**."
    elif frame.kind == OutboundFrameKind.ERROR:
        text = frame.text or "Something went wrong; please try again."
    else:
        return None

    if not text.strip():
        return None

    activity: dict[str, Any] = {
        "type": "message",
        "text": text,
        "conversation": {"id": conversation_ref},
    }
    if reply_to_id is not None:
        activity["replyToId"] = reply_to_id
    return activity


__all__ = ["to_reply_activity"]
