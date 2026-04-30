"""Translate runtime ``TurnEvent``-shaped tuples into ``OutboundFrame``s.

The runtime emits ``loop.types.TurnEvent`` instances; channels speak
``OutboundFrame``. We accept the lightweight ``(type, payload)`` shape
to avoid a hard dependency on ``loop-sdk-py`` from this core package
-- callers (channels-web, channels-slack, etc.) already adapt the
runtime stream and pass the parts through.

The mapping is intentionally narrow: only the kinds that are
meaningful on a wire are surfaced. Internal-only events (``trace``,
``retrieval``) return ``None`` and are dropped before serialisation.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from loop_channels_core.frames import OutboundFrame, OutboundFrameKind

# Map TurnEvent.type -> OutboundFrameKind. Anything not in this map is
# dropped (internal-only / not on the wire).
_KIND_BY_TYPE: dict[str, OutboundFrameKind] = {
    "token": OutboundFrameKind.AGENT_TOKEN,
    "tool_call_start": OutboundFrameKind.TOOL_CALL_START,
    "tool_call_end": OutboundFrameKind.TOOL_CALL_END,
    "complete": OutboundFrameKind.AGENT_MESSAGE,
    "degrade": OutboundFrameKind.ERROR,
}


def from_turn_event(
    *,
    event_type: str,
    payload: dict[str, Any],
    conversation_id: UUID,
    sequence: int,
) -> OutboundFrame | None:
    """Project a runtime turn event onto an ``OutboundFrame``.

    Returns ``None`` for events that have no on-wire representation
    (``trace``, ``retrieval``, anything unknown).
    """
    kind = _KIND_BY_TYPE.get(event_type)
    if kind is None:
        return None

    text = ""
    flat: dict[str, str] = {}

    if kind is OutboundFrameKind.AGENT_TOKEN:
        text = str(payload.get("text", ""))
    elif kind is OutboundFrameKind.TOOL_CALL_START:
        flat = {
            "id": str(payload.get("id", "")),
            "name": str(payload.get("name", "")),
            "arguments": json.dumps(
                payload.get("arguments", {}),
                separators=(",", ":"),
                sort_keys=True,
            ),
        }
    elif kind is OutboundFrameKind.TOOL_CALL_END:
        result = payload.get("result")
        err = payload.get("error")
        flat = {
            "id": str(payload.get("id", "")),
            "name": str(payload.get("name", "")),
            "result": "" if result is None else str(result),
            "error": "" if err is None else str(err),
            "latency_ms": str(payload.get("latency_ms", 0)),
        }
    elif kind is OutboundFrameKind.AGENT_MESSAGE:
        # `complete` carries an AgentResponse with content[].text.
        content = payload.get("content") or []
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text = str(part.get("text", ""))
                    break
    elif kind is OutboundFrameKind.ERROR:
        flat = {
            "code": str(payload.get("reason", "runtime_error")),
        }
        text = str(payload.get("message", ""))

    return OutboundFrame(
        conversation_id=conversation_id,
        kind=kind,
        text=text,
        payload=flat,
        sequence=sequence,
    )


__all__ = ["from_turn_event"]
