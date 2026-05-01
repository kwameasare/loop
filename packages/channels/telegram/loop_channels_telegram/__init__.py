"""Loop Telegram channel.

Translates Telegram Bot API webhook updates into :class:`InboundEvent`
envelopes and translates the runtime's :class:`OutboundFrame` stream
into ``sendMessage`` request bodies. The host owns the HTTPS bot
endpoint and the outbound HTTP client.
"""

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
    "TelegramBotProfile",
    "TelegramChannel",
    "TelegramConnectFlow",
    "TelegramConnectRequest",
    "TelegramConnectResult",
    "TelegramConversationIndex",
    "parse_update",
    "to_send_message_body",
]
