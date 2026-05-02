"""VoiceSession orchestrator."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable

from loop_voice.models import VoiceTurn, VoiceTurnState
from loop_voice.protocols import (
    PrewarmableTextToSpeech,
    RealtimeTransport,
    SpeechToText,
    TextToSpeech,
)

# An async function that takes the user's transcribed utterance and
# returns the agent's reply text. Real wiring goes to TurnExecutor.
AgentResponder = Callable[[str], Awaitable[str]]
StreamingAgentResponder = Callable[[str], AsyncIterator[str]]


def _sentence_end(text: str) -> int | None:
    for idx, ch in enumerate(text):
        if ch not in ".?!\n":
            continue
        if idx == len(text) - 1 or text[idx + 1].isspace():
            return idx + 1
    return None


async def stream_sentence_boundaries(chunks: AsyncIterator[str]) -> AsyncIterator[str]:
    """Yield complete sentence-ish chunks and flush any trailing fragment."""

    buffer = ""
    async for chunk in chunks:
        if not chunk:
            continue
        buffer += chunk
        while (end := _sentence_end(buffer)) is not None:
            sentence = buffer[:end].strip()
            buffer = buffer[end:].lstrip()
            if sentence:
                yield sentence
    if buffer.strip():
        yield buffer.strip()


class VoiceSession:
    """One audio-in/audio-out session.

    Loop:
        1. Pull audio from ``transport.inbound()``.
        2. Stream into ``stt.transcribe()`` -> emit partials/finals.
        3. On each final transcript, call ``agent`` -> reply text.
        4. Stream reply through ``tts.synthesize()`` and pipe to
           ``transport.send()``.
        5. Record a `VoiceTurn` and append to ``turns``.

    The session ends when the transport's inbound stream completes,
    or when ``stop()`` is called.
    """

    def __init__(
        self,
        *,
        transport: RealtimeTransport,
        stt: SpeechToText,
        tts: TextToSpeech,
        agent: AgentResponder,
        streaming_agent: StreamingAgentResponder | None = None,
    ) -> None:
        self._transport = transport
        self._stt = stt
        self._tts = tts
        self._agent = agent
        self._streaming_agent = streaming_agent
        self.turns: list[VoiceTurn] = []
        self._stopped = False

    async def _prewarm_tts(self) -> None:
        if isinstance(self._tts, PrewarmableTextToSpeech):
            await self._tts.prewarm()

    async def run(self) -> list[VoiceTurn]:
        async for transcript in self._stt.transcribe(self._transport.inbound()):
            if self._stopped:
                break
            if not transcript.is_final:
                continue
            started = time.monotonic()
            prewarm = asyncio.create_task(self._prewarm_tts())
            if self._streaming_agent is None:
                reply = await self._agent(transcript.text)
                await prewarm
                async for frame in self._tts.synthesize(reply):
                    await self._transport.send(frame)
            else:
                parts: list[str] = []
                prewarm_awaited = False
                async for sentence in stream_sentence_boundaries(
                    self._streaming_agent(transcript.text)
                ):
                    parts.append(sentence)
                    await prewarm
                    prewarm_awaited = True
                    async for frame in self._tts.synthesize(sentence):
                        await self._transport.send(frame)
                if not prewarm_awaited:
                    await prewarm
                reply = " ".join(parts)
            elapsed_ms = int((time.monotonic() - started) * 1000)
            self.turns.append(
                VoiceTurn(
                    user_text=transcript.text,
                    agent_text=reply,
                    state=VoiceTurnState.DONE,
                    duration_ms=elapsed_ms,
                )
            )
        return self.turns

    async def stop(self) -> None:
        self._stopped = True
        await self._transport.close()


__all__ = [
    "AgentResponder",
    "StreamingAgentResponder",
    "VoiceSession",
    "stream_sentence_boundaries",
]
