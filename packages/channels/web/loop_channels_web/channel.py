"""WebChannel: framework-agnostic REST + SSE adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator

from loop_channels_core import (
    ChannelDispatcher,
    InboundEvent,
    OutboundFrame,
)

from loop_channels_web.sse import sse_serialise


class WebChannel:
    """Bridges HTTP requests to a `ChannelDispatcher`.

    Wire-up:
        * `POST /messages` -> caller deserialises JSON into an
          `InboundEvent`, then awaits `handle(event)` and forwards
          the returned `bytes` iterator as `text/event-stream`.
        * `GET /messages/stream?conversation_id=...` -> identical
          handling; the difference is purely transport choice.
    """

    name: str = "web"

    def __init__(self) -> None:
        self._dispatcher: ChannelDispatcher | None = None

    async def start(self, dispatcher: ChannelDispatcher) -> None:
        self._dispatcher = dispatcher

    async def stop(self) -> None:
        self._dispatcher = None

    def handle(self, event: InboundEvent) -> AsyncIterator[bytes]:
        """Run the dispatcher and yield SSE-serialised bytes."""
        if self._dispatcher is None:
            raise RuntimeError("WebChannel.start() not called")
        return self._stream(event)

    async def _stream(self, event: InboundEvent) -> AsyncIterator[bytes]:
        assert self._dispatcher is not None
        async for frame in self._dispatcher.dispatch(event):
            yield sse_serialise(frame)

    async def collect(self, event: InboundEvent) -> list[OutboundFrame]:
        """Helper: drain the dispatcher into a list of frames (no SSE)."""
        if self._dispatcher is None:
            raise RuntimeError("WebChannel.start() not called")
        return [f async for f in self._dispatcher.dispatch(event)]


__all__ = ["WebChannel"]
