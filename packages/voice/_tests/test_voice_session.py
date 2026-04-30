from __future__ import annotations

import pytest
from loop_voice import (
    AudioFrame,
    InMemoryRealtimeTransport,
    InMemorySpeechToText,
    InMemoryTextToSpeech,
    Transcript,
    VoiceSession,
    VoiceTurnState,
)


async def _drain(it):  # pragma: no cover - utility
    return [x async for x in it]


@pytest.mark.asyncio
async def test_voice_session_round_trip() -> None:
    transport = InMemoryRealtimeTransport()
    await transport.push_inbound(AudioFrame(pcm=b"\x00", sequence=0))
    await transport.push_inbound(AudioFrame(pcm=b"\x01", sequence=1))
    await transport.end_inbound()

    stt = InMemorySpeechToText(script=["hello", "what's the weather"])
    tts = InMemoryTextToSpeech()

    async def agent(user_text: str) -> str:
        return f"got: {user_text}"

    session = VoiceSession(transport=transport, stt=stt, tts=tts, agent=agent)
    turns = await session.run()

    assert [t.user_text for t in turns] == ["hello", "what's the weather"]
    assert all(t.state is VoiceTurnState.DONE for t in turns)
    assert all(t.agent_text.startswith("got: ") for t in turns)
    # Outbound audio was synthesised; counts equal len(reply) per turn.
    assert len(transport.outbound) == sum(len(t.agent_text) for t in turns)


@pytest.mark.asyncio
async def test_partial_transcripts_do_not_trigger_agent() -> None:
    transport = InMemoryRealtimeTransport()
    await transport.end_inbound()

    class PartialOnly:
        async def transcribe(self, audio):
            async for _ in audio:
                pass
            yield Transcript(text="...", is_final=False, confidence=0.5)

    calls: list[str] = []

    async def agent(user_text: str) -> str:
        calls.append(user_text)
        return ""

    session = VoiceSession(
        transport=transport,
        stt=PartialOnly(),
        tts=InMemoryTextToSpeech(),
        agent=agent,
    )
    turns = await session.run()
    assert turns == []
    assert calls == []


@pytest.mark.asyncio
async def test_stop_closes_transport() -> None:
    transport = InMemoryRealtimeTransport()
    await transport.end_inbound()
    session = VoiceSession(
        transport=transport,
        stt=InMemorySpeechToText(script=[]),
        tts=InMemoryTextToSpeech(),
        agent=lambda _: _async_str("noop"),
    )
    await session.stop()
    with pytest.raises(RuntimeError):
        await transport.send(AudioFrame(pcm=b"x", sequence=0))


async def _async_str(s: str) -> str:
    return s
