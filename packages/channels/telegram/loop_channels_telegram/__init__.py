"""Loop Telegram channel.

Translates Telegram Bot API webhook updates into :class:`InboundEvent`
envelopes and translates the runtime's :class:`OutboundFrame` stream
into ``sendMessage`` request bodies. The host owns the HTTPS bot
endpoint and the outbound HTTP client.
"""

from loop_channels_telegram.byoc import (
    ByocTelegramSender,
    TelegramMessageSender,
    TelegramTransportBuilder,
    build_byoc_telegram_sender,
)
from loop_channels_telegram.channel import TelegramChannel, TelegramConversationIndex
from loop_channels_telegram.connect import (
    TelegramBotProfile,
    TelegramConnectFlow,
    TelegramConnectRequest,
    TelegramConnectResult,
)
from loop_channels_telegram.messages import to_send_message_body
from loop_channels_telegram.parser import parse_update

__all__ = [
    "ByocTelegramSender",
    "TelegramBotProfile",
    "TelegramChannel",
    "TelegramConnectFlow",
    "TelegramConnectRequest",
    "TelegramConnectResult",
    "TelegramConversationIndex",
    "TelegramMessageSender",
    "TelegramTransportBuilder",
    "build_byoc_telegram_sender",
    "parse_update",
    "to_send_message_body",
]
