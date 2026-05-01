"""Loop WhatsApp channel adapter (Cloud API direct).

Implements webhook verification (hub.challenge GET handshake +
X-Hub-Signature-256 POST signature), event parsing (text + media
messages), Block Kit-equivalent serialisation, and a thread-aware
``WhatsAppChannel`` that bridges into a ``ChannelDispatcher``.
"""

from loop_channels_whatsapp.channel import ConversationIndex, WhatsAppChannel
from loop_channels_whatsapp.connect import (
    CLOUD_API_VERSION,
    WhatsAppBusinessAccount,
    WhatsAppConnectFlow,
    WhatsAppConnectRequest,
    WhatsAppConnectResult,
)
from loop_channels_whatsapp.messages import to_messages
from loop_channels_whatsapp.parser import parse_event
from loop_channels_whatsapp.verify import (
    SignatureError,
    verify_challenge,
    verify_signature,
)

__all__ = [
    "CLOUD_API_VERSION",
    "ConversationIndex",
    "SignatureError",
    "WhatsAppBusinessAccount",
    "WhatsAppChannel",
    "WhatsAppConnectFlow",
    "WhatsAppConnectRequest",
    "WhatsAppConnectResult",
    "parse_event",
    "to_messages",
    "verify_challenge",
    "verify_signature",
]
