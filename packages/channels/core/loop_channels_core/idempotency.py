"""Inbound webhook idempotency.

Closes P0.5g from the prod-readiness audit. Every channel provider
delivers webhooks with at-least-once semantics: Slack ships an
``X-Slack-Retry-Num`` header, Meta retries WhatsApp/Messenger payloads
through Graph delivery retries, Discord retries failed interactions,
SES emits SQS at-least-once, Twilio re-POSTs on non-200, etc. Without
a per-channel deduplication store, a retry produces a duplicate agent
run — burning provider tokens and confusing the conversation thread.

This module ships the cross-channel primitives:

* :class:`InboundIdempotencyStore` — a Protocol every channel adapter
  consumes. Implementations are free to use Redis (production),
  Postgres, or a TTL-bounded in-memory dict (single-pod dev).
* :class:`MemoryIdempotencyStore` — reference impl, single-process
  TTL'd. Suitable for tests + single-pod dev. Production uses Redis.
* :func:`provider_event_id_for_*` — per-channel helpers that distill
  a stable, dedup-grade key out of each provider's payload shape.
  These are the ONLY thing per-channel adapters need to learn.

Convention
==========
The dedup key is namespaced ``"{channel}:{provider_event_id}"`` so a
single store can serve every channel without collision. Channels MUST
use the helper from this module rather than inventing their own
ad-hoc key.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Final, Protocol

#: Default TTL for a dedup record. Provider retry windows vary
#: (Slack 30 min, Meta up to 24h, Discord ~5 min, SES SQS up to a few
#: days). 24h is the longest reasonable retry window; any retry
#: arriving after 24h is itself an anomaly and we'd rather a
#: duplicate run than a silently-dropped message.
DEFAULT_TTL_SECONDS: Final[int] = 24 * 3600


class InboundIdempotencyStore(Protocol):
    """Pluggable dedup backend.

    Implementations MUST guarantee that ``claim`` is atomic: if two
    callers race with the same key, exactly one returns True and the
    other False. Backends with weaker guarantees (e.g. SQL "INSERT...
    ON CONFLICT") are fine; they just need to expose this contract.
    """

    def claim(self, key: str, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> bool:
        """Atomically claim ``key`` for ``ttl_seconds``.

        Returns True if this caller is the first to claim the key
        (the inbound is fresh; process it). Returns False if some
        other caller has already claimed it (the inbound is a retry;
        ack and drop).
        """
        ...


@dataclass(slots=True)
class MemoryIdempotencyStore:
    """In-process TTL-bounded dedup store.

    Single-pod dev / tests only. Production uses a shared backend
    (Redis or Postgres) so multiple replicas don't each accept the
    same retry. Time source is injectable for tests.
    """

    _records: dict[str, float] = field(default_factory=dict)
    _now: callable = field(default=time.time)  # type: ignore[assignment]

    def claim(self, key: str, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> bool:
        now = self._now()
        # Drop expired keys lazily; cheap in dev, redundant in
        # production-Redis (TTL handled by the server).
        expired = [k for k, exp in self._records.items() if exp <= now]
        for k in expired:
            del self._records[k]
        if key in self._records:
            return False
        self._records[key] = now + ttl_seconds
        return True


def make_dedup_key(channel: str, provider_event_id: str) -> str:
    """Compose a namespaced dedup key.

    The provider event id is appended verbatim (no further hashing)
    so operators can grep dedup hits by Slack message_ts / Meta WAMID
    / etc.
    """
    if not channel or not provider_event_id:
        raise ValueError("channel and provider_event_id must be non-empty")
    return f"{channel}:{provider_event_id}"


# --------------------------------------------------------------------------- #
# Per-channel event-id distillers                                             #
# --------------------------------------------------------------------------- #


def provider_event_id_for_slack(payload: dict[str, Any]) -> str:
    """Slack uses ``event_id`` (top-level) for events-api, or
    ``payload.message_ts`` for slash commands. We prefer the
    explicit ``event_id`` when present and fall back to a hash."""
    eid = payload.get("event_id")
    if isinstance(eid, str) and eid:
        return eid
    event = payload.get("event") or {}
    if isinstance(event, dict):
        ts = event.get("ts") or event.get("event_ts")
        if isinstance(ts, str) and ts:
            return f"event-ts-{ts}"
    return _content_hash(payload)


def provider_event_id_for_whatsapp(payload: dict[str, Any]) -> str:
    """WhatsApp Cloud API: every message has a ``messages[].id`` —
    Meta calls these WAMIDs (e.g. ``wamid.HBgL...``). For statuses,
    use the matching ``statuses[].id``."""
    entries = payload.get("entry") or []
    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            for change in entry.get("changes") or []:
                if not isinstance(change, dict):
                    continue
                value = change.get("value") or {}
                if not isinstance(value, dict):
                    continue
                for kind in ("messages", "statuses"):
                    items = value.get(kind) or []
                    if isinstance(items, list) and items:
                        for item in items:
                            if isinstance(item, dict) and isinstance(
                                item.get("id"), str
                            ):
                                return f"{kind[:-1]}-{item['id']}"
    return _content_hash(payload)


def provider_event_id_for_discord(payload: dict[str, Any]) -> str:
    """Discord interactions API: ``id`` is a snowflake unique to this
    interaction. For gateway message events, ``id`` on the inner
    message object."""
    iid = payload.get("id")
    if isinstance(iid, str) and iid:
        return iid
    msg = payload.get("d") or payload.get("data") or {}
    if isinstance(msg, dict) and isinstance(msg.get("id"), str):
        return f"msg-{msg['id']}"
    return _content_hash(payload)


def provider_event_id_for_telegram(payload: dict[str, Any]) -> str:
    """Telegram updates have a monotonic integer ``update_id`` that
    is unique per bot. We prefix with the bot id (when available)
    so multi-bot installations don't collide."""
    update_id = payload.get("update_id")
    if isinstance(update_id, int):
        return f"update-{update_id}"
    return _content_hash(payload)


def provider_event_id_for_twilio(payload: dict[str, Any] | str) -> str:
    """Twilio: form-encoded webhooks include ``MessageSid`` (e.g.
    ``SM...``). Each delivery retry of the same SID = same logical
    message."""
    if isinstance(payload, dict):
        sid = payload.get("MessageSid") or payload.get("messageSid")
        if isinstance(sid, str) and sid:
            return f"sid-{sid}"
        smid = payload.get("SmsMessageSid") or payload.get("smsMessageSid")
        if isinstance(smid, str) and smid:
            return f"sms-{smid}"
    return _content_hash(payload)


def provider_event_id_for_teams(payload: dict[str, Any]) -> str:
    """Bot Framework activities have ``id`` that's unique within a
    conversation. Combine with conversation.id to disambiguate
    cross-tenant collisions."""
    iid = payload.get("id")
    conv = payload.get("conversation") or {}
    conv_id = conv.get("id") if isinstance(conv, dict) else None
    if isinstance(iid, str) and isinstance(conv_id, str):
        return f"{conv_id}:{iid}"
    if isinstance(iid, str):
        return iid
    return _content_hash(payload)


def provider_event_id_for_email(payload: dict[str, Any]) -> str:
    """Email: SES gives us ``Records[].ses.mail.messageId`` for the
    SNS-wrapped flow, or we can fall back to the parsed
    ``Message-ID`` header from the MIME blob."""
    records = payload.get("Records") or []
    if isinstance(records, list):
        for rec in records:
            if not isinstance(rec, dict):
                continue
            ses = rec.get("ses") or rec.get("Ses") or {}
            mail = ses.get("mail") if isinstance(ses, dict) else None
            mid = mail.get("messageId") if isinstance(mail, dict) else None
            if isinstance(mid, str) and mid:
                return f"ses-{mid}"
    msg_id = payload.get("Message-ID") or payload.get("message_id")
    if isinstance(msg_id, str) and msg_id:
        return f"mime-{msg_id}"
    return _content_hash(payload)


def provider_event_id_for_rcs(payload: dict[str, Any]) -> str:
    """Google RCS Business Messaging: every event has a top-level
    ``messageId`` (UUID) that uniquely identifies the delivery."""
    mid = payload.get("messageId") or payload.get("message_id")
    if isinstance(mid, str) and mid:
        return f"rcs-{mid}"
    return _content_hash(payload)


def provider_event_id_for_web(payload: dict[str, Any]) -> str:
    """Loop's first-party web channel: clients pass a UUID per send
    (the SDK's `clientMessageId`); fall back to a hash if absent."""
    cmid = payload.get("clientMessageId") or payload.get("client_message_id")
    if isinstance(cmid, str) and cmid:
        return f"web-{cmid}"
    return _content_hash(payload)


def _content_hash(payload: Any) -> str:
    """Stable content-hash fallback when the provider didn't ship a
    natural unique id. SHA-256 over the canonicalised JSON bytes."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "ch-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


def keys_for_payloads(
    *,
    channel: str,
    payloads: Iterable[Any],
    extractor: callable,  # type: ignore[type-arg]
) -> list[str]:
    """Map a batch of provider payloads to namespaced dedup keys."""
    return [make_dedup_key(channel, extractor(p)) for p in payloads]


__all__ = [
    "DEFAULT_TTL_SECONDS",
    "InboundIdempotencyStore",
    "MemoryIdempotencyStore",
    "keys_for_payloads",
    "make_dedup_key",
    "provider_event_id_for_discord",
    "provider_event_id_for_email",
    "provider_event_id_for_rcs",
    "provider_event_id_for_slack",
    "provider_event_id_for_teams",
    "provider_event_id_for_telegram",
    "provider_event_id_for_twilio",
    "provider_event_id_for_web",
    "provider_event_id_for_whatsapp",
]
