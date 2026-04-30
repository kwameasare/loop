"""SSE serialisation for OutboundFrames.

Wire format follows the `text/event-stream` spec: each frame becomes a
named event with a JSON data payload, terminated by a blank line.

The ``event`` name maps directly from ``OutboundFrameKind`` so clients
can register one listener per kind.
"""

from __future__ import annotations

import json

from loop_channels_core import OutboundFrame


def sse_serialise(frame: OutboundFrame) -> bytes:
    payload = {
        "id": str(frame.id),
        "conversation_id": str(frame.conversation_id),
        "sequence": frame.sequence,
        "text": frame.text,
        "payload": frame.payload,
    }
    body = json.dumps(payload, separators=(",", ":"))
    # SSE: each line prefixed; double newline ends the event.
    msg = f"event: {frame.kind.value}\nid: {frame.id}\ndata: {body}\n\n"
    return msg.encode("utf-8")


__all__ = ["sse_serialise"]
