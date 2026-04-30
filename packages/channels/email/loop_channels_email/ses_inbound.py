"""SES inbound S3-trigger adapter (S513).

AWS SES is configured to write inbound MIME blobs into an S3 bucket
and emit an SNS event listing the new objects. This adapter:

1. Accepts the SNS event dict and yields S3 keys (one per inbound
   message).
2. Parses an RFC-822 MIME blob via the stdlib ``email`` package into
   a strict ``ParsedEmail`` (no HTML; we only keep ``text/plain``).
3. Surfaces references / in-reply-to so the threading module
   (S515) can correlate.

The S3 fetch itself is a callable parameter so unit tests don't need
moto/S3.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from email import message_from_bytes
from email.message import Message
from email.utils import getaddresses, parseaddr
from typing import Any


class SesInboundError(ValueError):
    """Inbound SES payload could not be parsed."""


@dataclass(frozen=True, slots=True)
class S3ObjectRef:
    """One S3 object pointed at by an SNS notification."""

    bucket: str
    key: str


@dataclass(frozen=True, slots=True)
class ParsedEmail:
    """Loop's strict view of an inbound RFC-822 message."""

    from_address: str
    to_addresses: tuple[str, ...]
    cc_addresses: tuple[str, ...]
    subject: str
    body_text: str
    message_id: str | None
    in_reply_to: str | None
    references: tuple[str, ...]


def parse_s3_event(event: dict[str, Any]) -> list[S3ObjectRef]:
    """Extract S3 object refs from an SNS-wrapped S3 event.

    The standard envelope is ``{"Records": [{"s3": {"bucket": {"name":
    ...}, "object": {"key": ...}}}]}``. We accept lower- or
    PascalCase keys for compat across SNS/SQS variants.
    """
    records = event.get("Records") or event.get("records")
    if not records:
        raise SesInboundError("no Records in event")
    out: list[S3ObjectRef] = []
    for rec in records:
        s3 = rec.get("s3") or rec.get("S3") or {}
        bucket = (s3.get("bucket") or s3.get("Bucket") or {}).get("name") or (
            s3.get("bucket") or s3.get("Bucket") or {}
        ).get("Name")
        key = (s3.get("object") or s3.get("Object") or {}).get("key") or (
            s3.get("object") or s3.get("Object") or {}
        ).get("Key")
        if not bucket or not key:
            raise SesInboundError(f"record missing bucket or key: {rec!r}")
        out.append(S3ObjectRef(bucket=bucket, key=key))
    return out


def _decode_part(part: Message) -> str:
    """Decode a non-multipart text part into a unicode string."""
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except (LookupError, UnicodeDecodeError):
        return payload.decode("utf-8", errors="replace")


def _first_text_plain(msg: Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return _decode_part(part)
        return ""
    if msg.get_content_type() == "text/plain":
        return _decode_part(msg)
    return ""


def parse_rfc822(blob: bytes) -> ParsedEmail:
    """Parse a raw MIME blob into a strict ``ParsedEmail``."""
    if not blob:
        raise SesInboundError("empty MIME blob")
    msg = message_from_bytes(blob)
    from_header = msg.get("From", "")
    _, from_addr = parseaddr(from_header)
    if not from_addr:
        raise SesInboundError("missing From header")
    to_addrs = tuple(addr for _, addr in getaddresses(msg.get_all("To") or []) if addr)
    cc_addrs = tuple(addr for _, addr in getaddresses(msg.get_all("Cc") or []) if addr)
    subject = msg.get("Subject", "") or ""
    body = _first_text_plain(msg)
    message_id = msg.get("Message-ID")
    in_reply_to = msg.get("In-Reply-To")
    refs_header = msg.get("References", "") or ""
    references = tuple(t for t in refs_header.split() if t.startswith("<"))
    return ParsedEmail(
        from_address=from_addr,
        to_addresses=to_addrs,
        cc_addresses=cc_addrs,
        subject=subject,
        body_text=body.strip(),
        message_id=message_id,
        in_reply_to=in_reply_to,
        references=references,
    )


@dataclass(slots=True)
class SesInboundIngester:
    """End-to-end: SNS event → list of ParsedEmail."""

    fetch_object: Callable[[S3ObjectRef], Awaitable[bytes]]

    async def ingest(self, event: dict[str, Any]) -> list[ParsedEmail]:
        refs = parse_s3_event(event)
        out: list[ParsedEmail] = []
        for ref in refs:
            blob = await self.fetch_object(ref)
            out.append(parse_rfc822(blob))
        return out


__all__ = [
    "ParsedEmail",
    "S3ObjectRef",
    "SesInboundError",
    "SesInboundIngester",
    "parse_rfc822",
    "parse_s3_event",
]
