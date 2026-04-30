"""Translate OutboundFrames into Telegram ``sendMessage`` bodies."""

from __future__ import annotations

from typing import Any

from loop_channels_core import OutboundFrame, OutboundFrameKind


def to_send_message_body(
    frame: OutboundFrame,
    *,
    chat_id: int,
    reply_to_message_id: int | None = None,
) -> dict[str, Any] | None:
    """Map a single :class:`OutboundFrame` to a ``sendMessage`` body.

    Streaming token frames are dropped: the runtime emits a final
    ``AGENT_MESSAGE`` frame which is what Telegram wants. Returns
    ``None`` for frames that should not produce a Telegram message.
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
        text = f"Handed off to {target}."
    elif frame.kind == OutboundFrameKind.ERROR:
        text = frame.text or "Something went wrong; please try again."
    else:
        return None

    if not text.strip():
        return None

    body: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if reply_to_message_id is not None:
        body["reply_to_message_id"] = reply_to_message_id
    return body


__all__ = ["to_send_message_body"]
