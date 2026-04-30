"""Render `OutboundFrame`s as Slack chat.postMessage payloads."""

from __future__ import annotations

from typing import Any

from loop_channels_core import OutboundFrame, OutboundFrameKind


def to_blocks(frame: OutboundFrame) -> dict[str, Any]:
    """Return a Slack ``chat.postMessage`` body for ``frame``.

    Token frames are filtered out -- Slack does not stream; only
    full agent_message / handoff / error frames produce posts.
    """
    if frame.kind is OutboundFrameKind.AGENT_TOKEN:
        # Tokens are coalesced into final agent_message frames upstream.
        return {}

    if frame.kind is OutboundFrameKind.AGENT_MESSAGE:
        return {
            "text": frame.text,
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": frame.text},
                }
            ],
        }

    if frame.kind is OutboundFrameKind.HANDOFF:
        target = frame.payload.get("target", "another agent")
        return {
            "text": f"Handing off to {target}.",
            "blocks": [
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f":arrows_counterclockwise: Handed off to *{target}*.",
                        }
                    ],
                }
            ],
        }

    if frame.kind is OutboundFrameKind.ERROR:
        code = frame.payload.get("code", "LOOP-RUNTIME-000")
        return {
            "text": f"[{code}] {frame.text}",
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f":warning: *{code}* -- {frame.text}"},
                }
            ],
        }

    if frame.kind in (
        OutboundFrameKind.TOOL_CALL_START,
        OutboundFrameKind.TOOL_CALL_END,
        OutboundFrameKind.DONE,
    ):
        return {}

    return {}  # pragma: no cover - exhaustive enum


__all__ = ["to_blocks"]
