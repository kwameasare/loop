"""Loop channel-layer abstractions.

A `Channel` is the bridge between an external surface (web, Slack,
WhatsApp, voice, etc.) and the agent runtime. Each channel must:

* Translate surface-native messages into ``InboundEvent`` instances.
* Stream agent ``OutboundFrame`` instances back to the surface.

Concrete channels live in sibling packages
(`loop_channels_web`, `loop_channels_slack`, `loop_channels_whatsapp`).
"""

from loop_channels_core.feature_matrix import (
    AgentChannelMatrix,
    ChannelCapability,
    ChannelFeatureProfile,
    default_channel_profiles,
)
from loop_channels_core.frames import (
    InboundEvent,
    InboundEventKind,
    OutboundFrame,
    OutboundFrameKind,
)
from loop_channels_core.idempotency import (
    DEFAULT_TTL_SECONDS,
    InboundIdempotencyStore,
    MemoryIdempotencyStore,
    make_dedup_key,
    provider_event_id_for_discord,
    provider_event_id_for_email,
    provider_event_id_for_rcs,
    provider_event_id_for_slack,
    provider_event_id_for_teams,
    provider_event_id_for_telegram,
    provider_event_id_for_twilio,
    provider_event_id_for_web,
    provider_event_id_for_whatsapp,
)
from loop_channels_core.protocol import (
    Channel,
    ChannelDispatcher,
    DispatcherFn,
    from_async_generator,
    from_list_factory,
    to_dispatcher,
)
from loop_channels_core.translate import from_turn_event

__all__ = [
    "DEFAULT_TTL_SECONDS",
    "AgentChannelMatrix",
    "Channel",
    "ChannelCapability",
    "ChannelDispatcher",
    "ChannelFeatureProfile",
    "DispatcherFn",
    "InboundEvent",
    "InboundEventKind",
    "InboundIdempotencyStore",
    "MemoryIdempotencyStore",
    "OutboundFrame",
    "OutboundFrameKind",
    "default_channel_profiles",
    "from_async_generator",
    "from_list_factory",
    "from_turn_event",
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
    "to_dispatcher",
]
