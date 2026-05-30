"""BYOC credential resolution for the Telegram bot adapter.

Required fields (provider ``telegram``):

* ``bot_token`` — the ``<botId>:<secret>`` string BotFather hands out.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from loop_channels_core import (
    ByocCredentialsResolver,
    validate_required_credentials,
)
from loop_channels_core.frames import OutboundFrame

__all__ = [
    "ByocTelegramSender",
    "TelegramMessageSender",
    "TelegramTransportBuilder",
    "build_byoc_telegram_sender",
]


_REQUIRED_TELEGRAM_FIELDS = ("bot_token",)


class TelegramMessageSender(Protocol):
    """Wraps the actual Bot API send (``POST
    https://api.telegram.org/bot<token>/sendMessage``)."""

    def send(self, *, frame: OutboundFrame, chat_id: str) -> dict[str, Any]: ...


class TelegramTransportBuilder(Protocol):
    def __call__(self, credentials: dict[str, Any]) -> TelegramMessageSender: ...


def _validate(creds: dict[str, Any]) -> None:
    validate_required_credentials(
        creds, required=_REQUIRED_TELEGRAM_FIELDS, provider="telegram"
    )


def build_byoc_telegram_sender(
    *,
    agent_id: UUID,
    resolver: ByocCredentialsResolver,
    transport_builder: TelegramTransportBuilder,
    channel_type: str = "telegram",
) -> TelegramMessageSender:
    creds = resolver(agent_id=agent_id, channel_type=channel_type)
    _validate(creds)
    return transport_builder(creds)


class ByocTelegramSender:
    def __init__(
        self,
        *,
        agent_id: UUID,
        resolver: ByocCredentialsResolver,
        transport_builder: TelegramTransportBuilder,
        channel_type: str = "telegram",
    ) -> None:
        self._agent_id = agent_id
        self._channel_type = channel_type
        self._resolver = resolver
        self._transport_builder = transport_builder

    def send(self, *, frame: OutboundFrame, chat_id: str) -> dict[str, Any]:
        creds = self._resolver(
            agent_id=self._agent_id, channel_type=self._channel_type
        )
        _validate(creds)
        upstream = self._transport_builder(creds)
        return upstream.send(frame=frame, chat_id=chat_id)
