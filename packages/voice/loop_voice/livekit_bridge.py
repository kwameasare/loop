"""LiveKit→Loop turn bridge (S369).

Bridges a LiveKit room's audio track into Loop's voice pipeline:

* inbound LiveKit audio frames are converted into ``AudioFrame``s and
  pushed into the Loop ``RealtimeTransport``,
* outbound ``AudioFrame``s from the agent (TTS output) are written
  back to LiveKit as published track data.

LiveKit's actual SDK is hidden behind a tiny Protocol so the bridge
can be unit-tested without an actual room.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from loop_voice.models import AudioFrame
from loop_voice.protocols import RealtimeTransport


@runtime_checkable
class LiveKitAudioTrack(Protocol):
    """A bidirectional LiveKit audio track wrapper."""

    async def frames(self) -> AsyncIterator[bytes]: ...

    async def publish(self, pcm: bytes) -> None: ...

    async def aclose(self) -> None: ...


@dataclass(slots=True)
class BridgeStats:
    """Telemetry counters surfaced for observability hooks."""

    inbound_frames: int = 0
    outbound_frames: int = 0
    dropped_inbound: int = 0
    inbound_bytes: int = 0
    outbound_bytes: int = 0


@dataclass(slots=True)
class LiveKitBridge:
    """Pumps audio between a LiveKit track and a Loop transport."""

    track: LiveKitAudioTrack
    transport: RealtimeTransport
    max_inbound_queue: int = 100
    stats: BridgeStats = field(default_factory=BridgeStats)
    _stop: asyncio.Event = field(default_factory=asyncio.Event)
    _seq_in: int = 0

    def __post_init__(self) -> None:
        if self.max_inbound_queue < 1:
            raise ValueError("max_inbound_queue must be >=1")

    async def _pump_inbound(
        self,
        on_frame: Callable[[AudioFrame], Awaitable[None]],
    ) -> None:
        """LiveKit → Loop: convert track frames to AudioFrame and dispatch."""
        async for pcm in self.track.frames():
            if self._stop.is_set():
                return
            self.stats.inbound_frames += 1
            self.stats.inbound_bytes += len(pcm)
            frame = AudioFrame(pcm=pcm, sequence=self._seq_in)
            self._seq_in += 1
            try:
                await asyncio.wait_for(on_frame(frame), timeout=1.0)
            except TimeoutError:
                self.stats.dropped_inbound += 1

    async def _pump_outbound(
        self, agent_audio: AsyncIterator[AudioFrame]
    ) -> None:
        """Loop → LiveKit: publish agent TTS audio."""
        async for frame in agent_audio:
            if self._stop.is_set():
                return
            await self.track.publish(frame.pcm)
            self.stats.outbound_frames += 1
            self.stats.outbound_bytes += len(frame.pcm)

    async def run(
        self,
        *,
        on_inbound: Callable[[AudioFrame], Awaitable[None]],
        agent_audio: AsyncIterator[AudioFrame],
    ) -> None:
        """Run both pumps until either side completes or stop() is called."""
        in_task = asyncio.create_task(self._pump_inbound(on_inbound))
        out_task = asyncio.create_task(self._pump_outbound(agent_audio))
        try:
            done, pending = await asyncio.wait(
                {in_task, out_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for t in pending:
                t.cancel()
            for t in done:
                exc = t.exception()
                if exc is not None:
                    raise exc
        finally:
            self._stop.set()
            await self.track.aclose()

    def stop(self) -> None:
        self._stop.set()


__all__ = [
    "BridgeStats",
    "LiveKitAudioTrack",
    "LiveKitBridge",
]
