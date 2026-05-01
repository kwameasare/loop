"""Loop Discord channel.

Translates Discord Interactions-API webhook payloads (slash command
or message component) and Bot Gateway message events into
:class:`InboundEvent` envelopes, and translates the runtime's
:class:`OutboundFrame` stream into Discord followup-message HTTP
bodies. The host service owns the HTTPS endpoint, signature
verification, and outbound HTTP client.

Inbound shape supported:
  * ``type == 2`` (APPLICATION_COMMAND, e.g. ``/ask <text>``); the
    first option's string value is taken as the prompt.
  * ``type == 3`` (MESSAGE_COMPONENT) -- ``custom_id`` becomes the
    prompt text.
"""

from loop_channels_discord.channel import (
    DiscordChannel,
    DiscordConversationIndex,
)
from loop_channels_discord.gateway import (
    DiscordBotProfile,
    DiscordConnectFlow,
    DiscordConnectRequest,
    DiscordConnectResult,
    DiscordGatewayMessageParser,
)
from loop_channels_discord.messages import to_followup_body
from loop_channels_discord.parser import parse_interaction

__all__ = [
    "DiscordBotProfile",
    "DiscordChannel",
    "DiscordConnectFlow",
    "DiscordConnectRequest",
    "DiscordConnectResult",
    "DiscordConversationIndex",
    "DiscordGatewayMessageParser",
    "parse_interaction",
    "to_followup_body",
]
