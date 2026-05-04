"""Telegram webhook receive mode (S518).

Telegram bots can run in two modes:
* long-polling (already implemented in long_poll.py for S517), or
* webhook — Telegram POSTs each ``Update`` to a configured HTTPS URL.

Webhook mode is mandatory for serverless / scale-to-zero deployments
where a long-poll loop is impractical. This module:

* Verifies Telegram's ``X-Telegram-Bot-Api-Secret-Token`` header in
  constant time.
* Parses the JSON envelope into a typed ``WebhookUpdate``.
* Dispatches into a caller-provided handler.

The actual HTTP transport (FastAPI/Starlette/Lambda) wires the
verifier + parser + dispatcher into its routing layer.
"""

from __future__ import annotations

import hmac
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Final
from uuid import UUID

from loop_channels_core import InboundEvent

from loop_channels_telegram.parser import parse_update

# Closes P0.5f: Telegram's secret-token header proves provenance but
# the payload has no timestamp in the verified surface. We gate on the
# embedded `message.date` (unix seconds) instead. Default 10 min skew
# accommodates Telegram's webhook retry behaviour (which can land
# minutes late on transient failures).
DEFAULT_MAX_EVENT_SKEW_SECONDS: Final[int] = 600


class TelegramWebhookError(ValueError):
    """Telegram webhook payload was rejected."""


def verify_secret_token(*, expected: str, received: str | None) -> bool:
    """Constant-time compare of the secret token header.

    Telegram sets this header to the value passed in
    ``setWebhook(secret_token=...)``. We use ``compare_digest`` so
    timing attacks can't probe the token bit-by-bit.
    """
    if not expected:
        raise TelegramWebhookError("expected token must be non-empty")
    if received is None:
        return False
    return hmac.compare_digest(expected.encode("utf-8"), received.encode("utf-8"))


@dataclass(frozen=True, slots=True)
class WebhookUpdate:
    """One parsed Telegram update with channel-routing context."""

    update_id: int
    event: InboundEvent | None
    chat_id: int | None
    raw: dict[str, Any]


def _walk_event_timestamps(payload: dict[str, Any]) -> list[int]:
    """Yield unix-second timestamps from any event-bearing sub-object
    in a Telegram update.

    Telegram updates can carry one of `message`, `edited_message`,
    `channel_post`, `callback_query`, etc. Each of those nests a
    `date` (unix seconds) we can gate on for replay protection.
    """
    out: list[int] = []
    candidate_keys = (
        "message",
        "edited_message",
        "channel_post",
        "edited_channel_post",
        "callback_query",
        "my_chat_member",
        "chat_member",
    )
    for key in candidate_keys:
        sub = payload.get(key)
        if not isinstance(sub, dict):
            continue
        # callback_query.message.date / message.date / etc.
        for path in (("date",), ("message", "date")):
            cur: Any = sub
            for k in path:
                if not isinstance(cur, dict):
                    cur = None
                    break
                cur = cur.get(k)
            if isinstance(cur, int):
                out.append(cur)
                break
    return out


def parse_webhook_body(
    body: bytes,
    *,
    workspace_id: UUID,
    agent_id: UUID,
    conversation_id: UUID,
    verify_event_timestamp: bool = True,
    max_event_skew_seconds: int = DEFAULT_MAX_EVENT_SKEW_SECONDS,
    now: float | None = None,
) -> WebhookUpdate:
    """Decode + parse a single webhook POST body.

    Closes P0.5f: when ``verify_event_timestamp`` is True (default),
    rejects updates whose embedded `date` is older than
    ``max_event_skew_seconds`` so a captured webhook can't be replayed.
    """
    if not body:
        raise TelegramWebhookError("empty webhook body")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise TelegramWebhookError(f"invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise TelegramWebhookError("payload must be a JSON object")
    update_id = payload.get("update_id")
    if not isinstance(update_id, int):
        raise TelegramWebhookError("update_id missing or not int")

    if verify_event_timestamp:
        timestamps = _walk_event_timestamps(payload)
        if timestamps:
            newest = max(timestamps)
            current = now if now is not None else time.time()
            if current - newest > max_event_skew_seconds:
                raise TelegramWebhookError(
                    "event timestamp outside replay window"
                )

    parsed = parse_update(
        payload,
        workspace_id=workspace_id,
        agent_id=agent_id,
        conversation_id=conversation_id,
    )
    if parsed is None:
        return WebhookUpdate(
            update_id=update_id, event=None, chat_id=None, raw=payload
        )
    event, chat_id = parsed
    return WebhookUpdate(
        update_id=update_id, event=event, chat_id=chat_id, raw=payload
    )


@dataclass(slots=True)
class TelegramWebhookHandler:
    """Production webhook entrypoint.

    Replay defense (P0.5f) is on by default via the embedded
    `message.date` timestamp. Operators backfilling historical
    updates can disable per-handler with
    ``verify_event_timestamp=False``.
    """

    expected_secret: str
    workspace_id: UUID
    agent_id: UUID
    conversation_id: UUID
    on_event: Callable[[InboundEvent, int], Awaitable[None]]
    verify_event_timestamp: bool = True
    max_event_skew_seconds: int = DEFAULT_MAX_EVENT_SKEW_SECONDS

    async def handle(self, *, body: bytes, secret_header: str | None) -> WebhookUpdate:
        if not verify_secret_token(
            expected=self.expected_secret, received=secret_header
        ):
            raise TelegramWebhookError("invalid secret token")
        update = parse_webhook_body(
            body,
            workspace_id=self.workspace_id,
            agent_id=self.agent_id,
            conversation_id=self.conversation_id,
            verify_event_timestamp=self.verify_event_timestamp,
            max_event_skew_seconds=self.max_event_skew_seconds,
        )
        if update.event is not None and update.chat_id is not None:
            await self.on_event(update.event, update.chat_id)
        return update


__all__ = [
    "TelegramWebhookError",
    "TelegramWebhookHandler",
    "WebhookUpdate",
    "parse_webhook_body",
    "verify_secret_token",
]
