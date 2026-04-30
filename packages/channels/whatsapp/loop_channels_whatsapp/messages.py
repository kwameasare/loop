"""Project ``OutboundFrame`` -> WhatsApp Cloud API request body.

Cloud API messages are POSTed to::

    POST https://graph.facebook.com/v18.0/{phone_number_id}/messages

with a JSON body shaped like::

    {"messaging_product": "whatsapp", "to": "<msisdn>", "type": "text", "text": {"body": "..."}}

We return the JSON body. The HTTP transport (httpx, retries, auth)
lives in the runtime so this module stays sync + dependency-free.
"""

from __future__ import annotations

from typing import Any

from loop_channels_core import OutboundFrame, OutboundFrameKind

MESSAGING_PRODUCT: str = "whatsapp"


def to_messages(frame: OutboundFrame, *, to: str) -> dict[str, Any]:
    """Serialise a single ``OutboundFrame`` to a Cloud API body.

    Returns an empty ``{}`` for frame kinds that have no surface
    representation (e.g. ``AGENT_TOKEN`` deltas, ``DONE`` markers,
    or ``TOOL_CALL_*`` brackets that should remain server-internal).
    """
    if frame.kind is OutboundFrameKind.AGENT_MESSAGE:
        return {
            "messaging_product": MESSAGING_PRODUCT,
            "to": to,
            "type": "text",
            "text": {"body": frame.text},
        }
    if frame.kind is OutboundFrameKind.HANDOFF:
        target = frame.payload.get("target", "")
        body = f"Handing off to {target}." if target else "Handing off."
        return {
            "messaging_product": MESSAGING_PRODUCT,
            "to": to,
            "type": "text",
            "text": {"body": body},
        }
    if frame.kind is OutboundFrameKind.ERROR:
        code = frame.payload.get("code", "error")
        return {
            "messaging_product": MESSAGING_PRODUCT,
            "to": to,
            "type": "text",
            "text": {"body": f"[{code}] {frame.text}".strip()},
        }
    return {}


__all__ = ["MESSAGING_PRODUCT", "to_messages"]
