"""Loop Microsoft Teams channel.

Translates Bot Framework activity payloads (delivered to a webhook
endpoint by the Bot Connector) into :class:`InboundEvent` envelopes
and translates the runtime's :class:`OutboundFrame` stream into
reply Activity bodies. The host service owns the HTTPS endpoint,
JWT validation, and the outbound HTTP client (``serviceUrl`` +
conversation id).
"""

from loop_channels_teams.channel import (
    TeamsChannel,
    TeamsConversationIndex,
)
from loop_channels_teams.connect import (
    TeamsAppManifest,
    TeamsConnectFlow,
    TeamsConnectRequest,
    TeamsConnectResult,
    render_adaptive_card,
)
from loop_channels_teams.messages import to_reply_activity
from loop_channels_teams.parser import parse_activity

__all__ = [
    "TeamsAppManifest",
    "TeamsChannel",
    "TeamsConnectFlow",
    "TeamsConnectRequest",
    "TeamsConnectResult",
    "TeamsConversationIndex",
    "parse_activity",
    "render_adaptive_card",
    "to_reply_activity",
]
