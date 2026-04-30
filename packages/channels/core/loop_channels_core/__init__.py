"""Loop channel-layer abstractions.

A `Channel` is the bridge between an external surface (web, Slack,
WhatsApp, voice, etc.) and the agent runtime. Each channel must:

* Translate surface-native messages into ``InboundEvent`` instances.
* Stream agent ``OutboundFrame`` instances back to the surface.

Concrete channels live in sibling packages
(`loop_channels_web`, `loop_channels_slack`, `loop_channels_whatsapp`).
"""

from loop_channels_core.frames import (
    InboundEvent,
    InboundEventKind,
    OutboundFrame,
    OutboundFrameKind,
)
from loop_channels_core.protocol import (
    Channel,
    ChannelDispatcher,
    DispatcherFn,
    from_async_generator,
    from_list_factory,
    to_dispatcher,
)

__all__ = [
    "Channel",
    "ChannelDispatcher",
    "DispatcherFn",
    "InboundEvent",
    "InboundEventKind",
    "OutboundFrame",
    "OutboundFrameKind",
    "from_async_generator",
    "from_list_factory",
    "to_dispatcher",
]
