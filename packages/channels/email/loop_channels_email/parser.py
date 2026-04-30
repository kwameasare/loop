"""Parse SES inbound JSON into a Loop InboundEvent.

The SES "Action: SNS" notification format wraps the raw mail in
``mail`` + ``content`` keys. Production deployments usually use
"Action: S3" + a separate fetch step; the parser here accepts the
already-fetched JSON body so it stays small + testable.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from loop_channels_core import InboundEvent, InboundEventKind


def _strip_quoted_reply(body: str) -> str:
    """Drop the standard ``On <date>, <person> wrote:`` reply trailer.

    Real production parsers handle many variants; this covers the
    common Outlook + Gmail forms and is enough for the MVP.
    """
    lines = body.splitlines()
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(">"):
            break
        if (
            stripped.startswith("On ")
            and stripped.endswith("wrote:")
            and " " in stripped
        ):
            break
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def _extract_message_id(headers: list[dict[str, str]]) -> str | None:
    for header in headers:
        if header.get("name", "").lower() == "message-id":
            return header.get("value")
    return None


def _extract_thread_id(mail: dict[str, Any], message_id: str | None) -> str:
    """SES exposes ``commonHeaders.references`` (list); the first
    Message-ID in that chain is the thread root. Falls back to the
    current message-id when this is the first message of a thread."""
    common = mail.get("commonHeaders") or {}
    refs = common.get("references")
    if isinstance(refs, list) and refs:
        return str(refs[0])
    if isinstance(refs, str) and refs.strip():
        return refs.strip().split()[0]
    if message_id:
        return message_id
    # Fall back to the SES messageId if the headers gave us nothing.
    return str(mail.get("messageId", ""))


def parse_ses_inbound(
    payload: dict[str, Any],
    *,
    workspace_id: UUID,
    agent_id: UUID,
    conversation_id: UUID,
) -> tuple[InboundEvent, str] | None:
    """Parse a single SES inbound payload.

    Returns ``(event, sender)`` -- the sender address is needed by
    the channel layer to address the reply. Returns ``None`` for
    payloads that aren't actionable inbound mail (bounces, etc.).
    """

    if payload.get("notificationType") not in (None, "Received"):
        return None

    mail = payload.get("mail") or {}
    if not isinstance(mail, dict):
        return None

    common = mail.get("commonHeaders") or {}
    sender_list = common.get("from") or []
    sender = str(sender_list[0]) if sender_list else str(mail.get("source", ""))
    if not sender:
        return None

    subject = str(common.get("subject", ""))
    body = str(payload.get("content", "")).strip()
    cleaned = _strip_quoted_reply(body) if body else ""
    text = subject if not cleaned else f"{subject}\n\n{cleaned}" if subject else cleaned

    metadata: dict[str, str] = {"sender": sender}
    if subject:
        metadata["subject"] = subject

    headers = mail.get("headers")
    if isinstance(headers, list):
        message_id = _extract_message_id(headers)
        if message_id:
            metadata["message_id"] = message_id
            metadata["thread_id"] = _extract_thread_id(mail, message_id)

    event = InboundEvent(
        workspace_id=workspace_id,
        agent_id=agent_id,
        conversation_id=conversation_id,
        kind=InboundEventKind.MESSAGE,
        user_id=sender,
        text=text,
        metadata=metadata,
    )
    return event, sender


__all__ = ["parse_ses_inbound"]
