"""Translate OutboundFrames into Discord followup-message bodies."""

from __future__ import annotations

from typing import Any

from loop_channels_core import OutboundFrame, OutboundFrameKind

EPHEMERAL_FLAG = 1 << 6


def to_followup_body(frame: OutboundFrame) -> dict[str, Any] | None:
    """Map a :class:`OutboundFrame` to a Discord followup body.

    Streaming token frames are dropped. Errors are emitted with the
    ephemeral flag so they're only visible to the invoking user.
    """
    if frame.kind in (OutboundFrameKind.AGENT_TOKEN, OutboundFrameKind.DONE):
        return None

    if frame.kind == OutboundFrameKind.AGENT_MESSAGE:
        body: dict[str, Any] = {"content": frame.text or ""}
    elif frame.kind == OutboundFrameKind.TOOL_CALL_START:
        tool = frame.payload.get("tool", "tool")
        body = {"content": f"_Calling `{tool}`\u2026_"}
    elif frame.kind == OutboundFrameKind.TOOL_CALL_END:
        tool = frame.payload.get("tool", "tool")
        body = {"content": f"_Finished `{tool}`._"}
    elif frame.kind == OutboundFrameKind.HANDOFF:
        target = frame.payload.get("to", "human")
        body = {"content": f"Handed off to **{target}**."}
    elif frame.kind == OutboundFrameKind.ERROR:
        body = {
            "content": frame.text or "Something went wrong.",
            "flags": EPHEMERAL_FLAG,
        }
    else:
        return None

    content = body.get("content", "")
    if not isinstance(content, str) or not content.strip():
        return None
    return body


__all__ = ["EPHEMERAL_FLAG", "to_followup_body"]
