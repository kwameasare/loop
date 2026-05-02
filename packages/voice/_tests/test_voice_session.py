from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
from loop_voice import (
    AudioFrame,
    InMemoryRealtimeTransport,
    InMemorySpeechToText,
    InMemoryTextToSpeech,
    Transcript,
    VoiceSession,
    VoiceTurnState,
    stream_sentence_boundaries,
)


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
        async def transcribe(self, audio: AsyncIterator[AudioFrame]) -> AsyncIterator[Transcript]:
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


async def _chunks(parts: list[str]) -> AsyncIterator[str]:
    for part in parts:
        yield part


@pytest.mark.asyncio
async def test_sentence_boundaries_flush_complete_and_trailing_fragments() -> None:
    sentences = [
        s async for s in stream_sentence_boundaries(_chunks(["Hello", ". How ", "are you"]))
    ]
    assert sentences == ["Hello.", "How are you"]


@pytest.mark.asyncio
async def test_streaming_agent_starts_tts_before_reply_finishes() -> None:
    transport = InMemoryRealtimeTransport()
    await transport.push_inbound(AudioFrame(pcm=b"\x00", sequence=0))
    await transport.end_inbound()

    first_synth_started = asyncio.Event()
    allow_agent_finish = asyncio.Event()
    agent_finished = False

    async def streaming_agent(_: str) -> AsyncIterator[str]:
        nonlocal agent_finished
        yield "First sentence. "
        await allow_agent_finish.wait()
        agent_finished = True
        yield "Second sentence."

    async def unused_agent(_: str) -> str:
        raise AssertionError("streaming_agent should handle the turn")

    class RecordingTTS(InMemoryTextToSpeech):
        def __init__(self) -> None:
            super().__init__()
            self.texts: list[str] = []

        async def synthesize(self, text: str) -> AsyncIterator[AudioFrame]:
            self.texts.append(text)
            first_synth_started.set()
            async for frame in super().synthesize(text):
                yield frame

    tts = RecordingTTS()
    session = VoiceSession(
        transport=transport,
        stt=InMemorySpeechToText(script=["hello"]),
        tts=tts,
        agent=unused_agent,
        streaming_agent=streaming_agent,
    )

    run_task = asyncio.create_task(session.run())
    await asyncio.wait_for(first_synth_started.wait(), timeout=1)
    assert not agent_finished

    allow_agent_finish.set()
    turns = await run_task

    assert tts.prewarm_count == 1
    assert tts.texts == ["First sentence.", "Second sentence."]
    assert turns[0].agent_text == "First sentence. Second sentence."


@pytest.mark.asyncio
async def test_full_reply_path_prewarms_tts_before_synthesis() -> None:
    transport = InMemoryRealtimeTransport()
    await transport.push_inbound(AudioFrame(pcm=b"\x00", sequence=0))
    await transport.end_inbound()

    class RecordingTTS(InMemoryTextToSpeech):
        async def synthesize(self, text: str) -> AsyncIterator[AudioFrame]:
            assert self.prewarm_count == 1
            async for frame in super().synthesize(text):
                yield frame

    async def agent(_: str) -> str:
        return "full reply"

    session = VoiceSession(
        transport=transport,
        stt=InMemorySpeechToText(script=["hello"]),
        tts=RecordingTTS(),
        agent=agent,
    )

    turns = await session.run()
    assert turns[0].agent_text == "full reply"
