"""Loop web channel: REST + SSE adapter.

This package is FastAPI/Starlette-free at its core: ``WebChannel``
exposes two coroutines -- ``handle_post(event)`` and ``stream(event)``
-- that any HTTP framework can wire up. A thin Starlette application
factory is provided in ``loop_channels_web.app`` for convenience.
"""

from loop_channels_web.channel import WebChannel
from loop_channels_web.sse import sse_serialise

__all__ = ["WebChannel", "sse_serialise"]
