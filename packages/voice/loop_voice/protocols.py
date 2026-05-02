"""Provider Protocols + in-memory test impls."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from loop_voice.models import AudioFrame, Transcript


@runtime_checkable
class RealtimeTransport(Protocol):
    """Bidirectional audio transport (LiveKit room, WebRTC peer, ...)."""

    def inbound(self) -> AsyncIterator[AudioFrame]: ...

    async def send(self, frame: AudioFrame) -> None: ...

    async def close(self) -> None: ...


@runtime_checkable
class SpeechToText(Protocol):
    """Streaming ASR. Implementations consume an audio iterator and
    emit transcripts (partials + finals)."""

    def transcribe(self, audio: AsyncIterator[AudioFrame]) -> AsyncIterator[Transcript]: ...


@runtime_checkable
class TextToSpeech(Protocol):
    """Streaming TTS."""

    def synthesize(self, text: str) -> AsyncIterator[AudioFrame]: ...


@runtime_checkable
class PrewarmableTextToSpeech(TextToSpeech, Protocol):
    """TTS provider that can warm sockets/model state before text arrives."""

    async def prewarm(self) -> None: ...


# --------------------------------------------------------------------- impls


class InMemoryRealtimeTransport:
    """Async-queue backed transport for tests + studio dev runner."""

    def __init__(self) -> None:
        self._inbound: asyncio.Queue[AudioFrame | None] = asyncio.Queue()
        self.outbound: list[AudioFrame] = []
        self._closed = False

    async def push_inbound(self, frame: AudioFrame) -> None:
        await self._inbound.put(frame)

    async def end_inbound(self) -> None:
        await self._inbound.put(None)

    async def inbound(self) -> AsyncIterator[AudioFrame]:
        while True:
            frame = await self._inbound.get()
            if frame is None:
                return
            yield frame

    async def send(self, frame: AudioFrame) -> None:
        if self._closed:
            raise RuntimeError("transport closed")
        self.outbound.append(frame)

    async def close(self) -> None:
        self._closed = True
        await self._inbound.put(None)


class InMemorySpeechToText:
    """Deterministic ASR stub: each script entry yields one final
    transcript, optionally preceded by a partial."""

    def __init__(self, script: list[str]) -> None:
        self._script = list(script)

    async def transcribe(self, audio: AsyncIterator[AudioFrame]) -> AsyncIterator[Transcript]:
        # Drain audio so the source side completes naturally.
        i = 0
        async for _ in audio:
            if i < len(self._script):
                text = self._script[i]
                yield Transcript(
                    text=text[: max(1, len(text) // 2)], is_final=False, confidence=0.7
                )
                yield Transcript(text=text, is_final=True, confidence=0.95)
                i += 1


class InMemoryTextToSpeech:
    """Emit one frame per character. Sequence numbers start at 0
    *per call* so multiple replies in a session don't collide -- the
    transport assigns global ordering."""

    def __init__(self) -> None:
        self.prewarm_count = 0

    async def prewarm(self) -> None:
        self.prewarm_count += 1

    async def synthesize(self, text: str) -> AsyncIterator[AudioFrame]:
        for i, ch in enumerate(text):
            yield AudioFrame(pcm=ch.encode("utf-8"), sequence=i)


__all__ = [
    "InMemoryRealtimeTransport",
    "InMemorySpeechToText",
    "InMemoryTextToSpeech",
    "PrewarmableTextToSpeech",
    "RealtimeTransport",
    "SpeechToText",
    "TextToSpeech",
]
