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
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from loop_channels_core import InboundEvent

from loop_channels_telegram.parser import parse_update


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


def parse_webhook_body(
    body: bytes,
    *,
    workspace_id: UUID,
    agent_id: UUID,
    conversation_id: UUID,
) -> WebhookUpdate:
    """Decode + parse a single webhook POST body."""
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
    """Production webhook entrypoint."""

    expected_secret: str
    workspace_id: UUID
    agent_id: UUID
    conversation_id: UUID
    on_event: Callable[[InboundEvent, int], Awaitable[None]]

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
