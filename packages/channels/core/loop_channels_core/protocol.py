"""Channel + dispatcher protocols."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Protocol, runtime_checkable

from loop_channels_core.frames import InboundEvent, OutboundFrame


@runtime_checkable
class ChannelDispatcher(Protocol):
    """Implemented by the runtime; called by channels to drive a turn.

    Returns an async iterator of frames that the channel must serialise
    to its surface in order.
    """

    def dispatch(self, event: InboundEvent) -> AsyncIterator[OutboundFrame]: ...


@runtime_checkable
class Channel(Protocol):
    """A surface adapter."""

    @property
    def name(self) -> str: ...

    async def start(self, dispatcher: ChannelDispatcher) -> None: ...

    async def stop(self) -> None: ...


# Convenience: most channel impls accept a plain async function instead
# of a full Protocol object.
DispatcherFn = Callable[[InboundEvent], AsyncIterator[OutboundFrame]]


def to_dispatcher(fn: DispatcherFn) -> ChannelDispatcher:
    """Wrap a plain async-iterator-returning function as a dispatcher."""

    class _FnDispatcher:
        def dispatch(self, event: InboundEvent) -> AsyncIterator[OutboundFrame]:
            return fn(event)

    return _FnDispatcher()


# A second helper: take an async function that *yields* frames (i.e.
# is itself an async generator) -- which is the common case.
def from_async_generator(
    gen: Callable[[InboundEvent], AsyncIterator[OutboundFrame]],
) -> ChannelDispatcher:
    return to_dispatcher(gen)


# A third helper: from an async function returning a list (handy for tests).
def from_list_factory(
    factory: Callable[[InboundEvent], Awaitable[list[OutboundFrame]]],
) -> ChannelDispatcher:
    async def _gen(event: InboundEvent) -> AsyncIterator[OutboundFrame]:
        for frame in await factory(event):
            yield frame

    return to_dispatcher(_gen)


__all__ = [
    "Channel",
    "ChannelDispatcher",
    "DispatcherFn",
    "from_async_generator",
    "from_list_factory",
    "to_dispatcher",
]
