"""Translate OutboundFrames into SES SendEmail request bodies."""

from __future__ import annotations

from typing import Any

from loop_channels_core import OutboundFrame, OutboundFrameKind


def to_send_email_body(
    frame: OutboundFrame,
    *,
    to: str,
    sender: str,
    subject: str,
    in_reply_to: str | None = None,
) -> dict[str, Any] | None:
    """Map a single :class:`OutboundFrame` to an SES SendEmail body.

    Streaming token frames are dropped -- email is a non-streaming
    surface. Tool-call markers are folded into the body for transparency.
    Returns ``None`` for frames that should not produce an email
    (e.g. ``DONE``, ``AGENT_TOKEN``).
    """

    if frame.kind in (OutboundFrameKind.AGENT_TOKEN, OutboundFrameKind.DONE):
        return None

    if frame.kind == OutboundFrameKind.AGENT_MESSAGE:
        body_text = frame.text or ""
    elif frame.kind == OutboundFrameKind.TOOL_CALL_START:
        tool = frame.payload.get("tool", "tool")
        body_text = f"[Calling {tool}\u2026]"
    elif frame.kind == OutboundFrameKind.TOOL_CALL_END:
        tool = frame.payload.get("tool", "tool")
        body_text = f"[Finished {tool}.]"
    elif frame.kind == OutboundFrameKind.HANDOFF:
        target = frame.payload.get("to", "human")
        body_text = f"This conversation has been handed off to {target}."
    elif frame.kind == OutboundFrameKind.ERROR:
        body_text = frame.text or "Something went wrong; please try again."
    else:
        return None

    if not body_text.strip():
        return None

    reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"

    headers: list[dict[str, str]] = []
    if in_reply_to:
        headers.append({"Name": "In-Reply-To", "Value": in_reply_to})
        headers.append({"Name": "References", "Value": in_reply_to})

    body: dict[str, Any] = {
        "Source": sender,
        "Destination": {"ToAddresses": [to]},
        "Message": {
            "Subject": {"Data": reply_subject, "Charset": "UTF-8"},
            "Body": {"Text": {"Data": body_text, "Charset": "UTF-8"}},
        },
    }
    if headers:
        body["Headers"] = headers
    return body


__all__ = ["to_send_email_body"]
