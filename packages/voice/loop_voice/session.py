"""VoiceSession orchestrator."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from loop_voice.models import VoiceTurn, VoiceTurnState
from loop_voice.protocols import RealtimeTransport, SpeechToText, TextToSpeech

# An async function that takes the user's transcribed utterance and
# returns the agent's reply text. Real wiring goes to TurnExecutor.
AgentResponder = Callable[[str], Awaitable[str]]


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
    ) -> None:
        self._transport = transport
        self._stt = stt
        self._tts = tts
        self._agent = agent
        self.turns: list[VoiceTurn] = []
        self._stopped = False

    async def run(self) -> list[VoiceTurn]:
        async for transcript in self._stt.transcribe(self._transport.inbound()):
            if self._stopped:
                break
            if not transcript.is_final:
                continue
            started = time.monotonic()
            reply = await self._agent(transcript.text)
            async for frame in self._tts.synthesize(reply):
                await self._transport.send(frame)
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


__all__ = ["AgentResponder", "VoiceSession"]
