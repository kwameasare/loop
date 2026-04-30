"""End-to-end test for the voice MVP echo agent (S033).

Wires offer -> answer signaling -> a VoiceSession driving an echo
agent through InMemory transport/STT/TTS, and asserts the echoed
audio comes out the other side.
"""

from __future__ import annotations

from uuid import uuid4

from loop_voice import (
    AudioFrame,
    InMemoryRealtimeTransport,
    InMemorySpeechToText,
    InMemoryTextToSpeech,
    VoiceSession,
    VoiceTurnState,
    WebRTCSessionRegistry,
    WebRTCSessionState,
    WebRTCSignal,
    make_echo_agent,
)


async def test_webrtc_negotiate_then_echo_round_trip() -> None:
    # 1. Signaling: caller posts an SDP offer, server hands back an answer.
    registry = WebRTCSessionRegistry()
    session, answer = registry.negotiate(
        conversation_id=uuid4(),
        offer=WebRTCSignal(kind="offer", sdp="v=0\r\no=- caller IN IP4 0.0.0.0\r\n"),
        now_ms=1_000,
    )
    assert answer.kind == "answer"
    assert session.state is WebRTCSessionState.CONNECTED

    # 2. Media: with a "connected" peer, drive a VoiceSession with the
    # in-memory transport pinned to that session id (real adapter
    # wires aiortc here).
    transport = InMemoryRealtimeTransport()
    stt = InMemorySpeechToText(script=["hello world"])
    tts = InMemoryTextToSpeech()
    voice = VoiceSession(
        transport=transport,
        stt=stt,
        tts=tts,
        agent=make_echo_agent(prefix="echo: "),
    )

    # Push one user audio frame and end the inbound stream.
    await transport.push_inbound(AudioFrame(pcm=b"\x00\x01", sequence=0))
    await transport.end_inbound()

    turns = await voice.run()

    # 3. Assertions: the echo agent ran, TTS produced a frame per char.
    assert len(turns) == 1
    turn = turns[0]
    assert turn.user_text == "hello world"
    assert turn.agent_text == "echo: hello world"
    assert turn.state is VoiceTurnState.DONE
    expected_text = "echo: hello world"
    assert len(transport.outbound) == len(expected_text)
    decoded = b"".join(f.pcm for f in transport.outbound).decode("utf-8")
    assert decoded == expected_text

    # 4. Tear-down: signaling close.
    closed = registry.close(session.id, now_ms=2_000)
    assert closed.state is WebRTCSessionState.CLOSED
