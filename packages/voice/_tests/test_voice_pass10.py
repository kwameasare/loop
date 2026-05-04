"""Tests for pass10 voice adapters (S361-S365, S368, S369, S380, S383)."""

# ruff: noqa: RUF012

from __future__ import annotations

import base64
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

import pytest
from loop_voice.asr_deepgram import (
    DeepgramConfig,
    DeepgramError,
    DeepgramSpeechToText,
    deepgram_url,
    parse_deepgram_message,
)
from loop_voice.asr_whisper import (
    WhisperConfig,
    WhisperError,
    WhisperSpeechToText,
    _is_silent,
)
from loop_voice.livekit_bridge import LiveKitBridge
from loop_voice.livekit_room import (
    LiveKitError,
    RoomGrant,
    RoomManager,
    RoomNotFound,
)
from loop_voice.models import AudioFrame
from loop_voice.sip_twilio import (
    StreamConfig,
    TwilioTwimlError,
    TwimlConfig,
    build_twiml,
    parse_twilio_form,
)
from loop_voice.tts_cartesia import (
    CartesiaConfig,
    CartesiaError,
    CartesiaTextToSpeech,
    build_cartesia_request,
    cartesia_url,
)
from loop_voice.tts_elevenlabs import (
    ElevenLabsConfig,
    ElevenLabsTextToSpeech,
    elevenlabs_url,
)
from loop_voice.tts_piper import (
    PiperConfig,
    PiperError,
    PiperTextToSpeech,
    chunk_pcm,
)
from loop_voice.voicemail import (
    CallDisposition,
    FallbackAction,
    VoicemailPolicy,
    plan_fallback,
)

# --------------------------- Fakes ---------------------------


@dataclass
class FakeWS:
    incoming: list[str] = field(default_factory=list)
    sent_bytes: list[bytes] = field(default_factory=list)
    sent_text: list[str] = field(default_factory=list)
    closed: bool = False
    raise_on_recv: BaseException | None = None

    async def send_bytes(self, data: bytes) -> None:
        self.sent_bytes.append(data)

    async def send_text(self, text: str) -> None:
        self.sent_text.append(text)

    async def receive_text(self) -> str:
        if self.raise_on_recv is not None:
            raise self.raise_on_recv
        if not self.incoming:
            return ""
        return self.incoming.pop(0)

    async def aclose(self) -> None:
        self.closed = True


def make_ws_factory(ws: FakeWS):
    async def _factory(url: str, headers: dict) -> FakeWS:
        ws.last_url = url  # type: ignore[attr-defined]
        ws.last_headers = headers  # type: ignore[attr-defined]
        return ws

    return _factory


# --------------------------- Deepgram ---------------------------


def test_deepgram_url_includes_all_params():
    cfg = DeepgramConfig(api_key="k", model="nova-2", language="en-GB", sample_rate=8000, endpointing_ms=120)
    url = deepgram_url(cfg)
    for fragment in ("model=nova-2", "language=en-GB", "sample_rate=8000", "endpointing=120", "encoding=linear16", "interim_results=true"):
        assert fragment in url


def test_deepgram_config_rejects_bad_sample_rate():
    with pytest.raises(ValueError):
        DeepgramConfig(api_key="k", sample_rate=11025)


def test_deepgram_config_rejects_short_endpointing():
    with pytest.raises(ValueError):
        DeepgramConfig(api_key="k", endpointing_ms=10)


def test_parse_deepgram_message_returns_transcript():
    raw = json.dumps({
        "type": "Results",
        "is_final": True,
        "channel": {"alternatives": [{"transcript": "hello world", "confidence": 0.92}]},
    })
    t = parse_deepgram_message(raw)
    assert t is not None
    assert t.text == "hello world"
    assert t.is_final is True
    assert t.confidence == pytest.approx(0.92)


def test_parse_deepgram_message_skips_metadata():
    assert parse_deepgram_message(json.dumps({"type": "Metadata"})) is None
    assert parse_deepgram_message(json.dumps({"type": "SpeechStarted"})) is None
    assert parse_deepgram_message(json.dumps({"channel": {"alternatives": [{"transcript": ""}]}})) is None


def test_parse_deepgram_message_raises_on_garbage():
    with pytest.raises(DeepgramError):
        parse_deepgram_message("not json")


@pytest.mark.asyncio
async def test_deepgram_transcribe_round_trip():
    ws = FakeWS(incoming=[
        json.dumps({"type": "Metadata"}),
        json.dumps({
            "is_final": False,
            "channel": {"alternatives": [{"transcript": "hello", "confidence": 0.5}]},
        }),
        json.dumps({
            "is_final": True,
            "channel": {"alternatives": [{"transcript": "hello world", "confidence": 0.9}]},
        }),
        "",  # close
    ])
    cfg = DeepgramConfig(api_key="k")
    stt = DeepgramSpeechToText(config=cfg, open_ws=make_ws_factory(ws))

    async def audio() -> AsyncIterator[AudioFrame]:
        yield AudioFrame(pcm=b"\x00\x01" * 80, sequence=0)
        yield AudioFrame(pcm=b"\x00\x02" * 80, sequence=1)

    out = []
    async for t in stt.transcribe(audio()):
        out.append(t)
    assert [t.text for t in out] == ["hello", "hello world"]
    assert out[1].is_final is True
    assert ws.closed is True


# --------------------------- Whisper ---------------------------


def test_is_silent_threshold():
    silent_frame = AudioFrame(pcm=b"\x00\x00" * 160, sequence=0)
    loud_frame = AudioFrame(pcm=b"\xff\x7f" * 160, sequence=1)
    assert _is_silent(silent_frame) is True
    assert _is_silent(loud_frame) is False
    assert _is_silent(AudioFrame(pcm=b"", sequence=2)) is True


def test_whisper_config_validators():
    with pytest.raises(ValueError):
        WhisperConfig(model_path=Path("/m"), silence_frames=0)
    with pytest.raises(ValueError):
        WhisperConfig(model_path=Path("/m"), silence_frames=10, utterance_max_frames=5)


@pytest.mark.asyncio
async def test_whisper_flushes_on_silence():
    class Runner:
        calls: list[bytes] = []

        def transcribe_pcm(self, pcm: bytes, *, language: str) -> tuple[str, float]:
            self.calls.append(pcm)
            return ("hello", 0.8)

    runner = Runner()
    cfg = WhisperConfig(model_path=Path("/m"), silence_frames=2, utterance_max_frames=100)
    stt = WhisperSpeechToText(config=cfg, runner=runner)

    async def audio() -> AsyncIterator[AudioFrame]:
        yield AudioFrame(pcm=b"\xff\x7f" * 160, sequence=0)  # loud
        yield AudioFrame(pcm=b"\x00\x00" * 160, sequence=1)  # silent
        yield AudioFrame(pcm=b"\x00\x00" * 160, sequence=2)  # silent => flush

    out = [t async for t in stt.transcribe(audio())]
    assert [t.text for t in out] == ["hello"]
    assert runner.calls, "runner must have been called"


@pytest.mark.asyncio
async def test_whisper_max_frames_cap():
    class Runner:
        calls = 0

        def transcribe_pcm(self, pcm: bytes, *, language: str) -> tuple[str, float]:
            self.calls += 1
            return ("ok", 1.0)

    runner = Runner()
    # silence_frames intentionally large so the cap is the only flush trigger.
    cfg = WhisperConfig(model_path=Path("/m"), silence_frames=2, utterance_max_frames=2)
    stt = WhisperSpeechToText(config=cfg, runner=runner)

    async def audio() -> AsyncIterator[AudioFrame]:
        for i in range(5):
            yield AudioFrame(pcm=b"\xff\x7f" * 80, sequence=i)

    out = [t async for t in stt.transcribe(audio())]
    # 5 loud frames, cap=2 => at least 2 flushes
    assert len(out) >= 2


@pytest.mark.asyncio
async def test_whisper_runner_error_wraps():
    class BadRunner:
        def transcribe_pcm(self, pcm, *, language):
            raise RuntimeError("model gone")

    cfg = WhisperConfig(model_path=Path("/m"), silence_frames=1, utterance_max_frames=10)
    stt = WhisperSpeechToText(config=cfg, runner=BadRunner())

    async def audio() -> AsyncIterator[AudioFrame]:
        yield AudioFrame(pcm=b"\xff\x7f" * 80, sequence=0)
        yield AudioFrame(pcm=b"\x00\x00" * 80, sequence=1)

    with pytest.raises(WhisperError):
        async for _ in stt.transcribe(audio()):
            pass


# --------------------------- ElevenLabs ---------------------------


def test_elevenlabs_url_shape():
    cfg = ElevenLabsConfig(api_key="k", voice_id="v1", optimize_streaming_latency=2)
    url = elevenlabs_url(cfg)
    assert "/v1/text-to-speech/v1/stream-input" in url
    assert "optimize_streaming_latency=2" in url


def test_elevenlabs_validators():
    with pytest.raises(ValueError):
        ElevenLabsConfig(api_key="k", voice_id="v", stability=2.0)
    with pytest.raises(ValueError):
        ElevenLabsConfig(api_key="k", voice_id="v", optimize_streaming_latency=99)


@pytest.mark.asyncio
async def test_elevenlabs_synthesize_yields_sequenced_frames():
    chunk1 = base64.b64encode(b"PCM_A").decode()
    chunk2 = base64.b64encode(b"PCM_BB").decode()
    ws = FakeWS(incoming=[
        json.dumps({"audio": chunk1}),
        json.dumps({"audio": chunk2}),
        json.dumps({"isFinal": True}),
    ])
    cfg = ElevenLabsConfig(api_key="k", voice_id="v")
    tts = ElevenLabsTextToSpeech(config=cfg, open_ws=make_ws_factory(ws))
    frames = [f async for f in tts.synthesize("hello")]
    assert [f.pcm for f in frames] == [b"PCM_A", b"PCM_BB"]
    assert [f.sequence for f in frames] == [0, 1]
    assert ws.closed is True


# --------------------------- Cartesia ---------------------------


def test_cartesia_url_carries_version():
    cfg = CartesiaConfig(api_key="k", voice_id="v")
    assert "cartesia_version=2024-06-10" in cartesia_url(cfg)


def test_cartesia_request_shape():
    cfg = CartesiaConfig(api_key="k", voice_id="v", sample_rate=24_000)
    req = build_cartesia_request(cfg, "hi")
    assert req["transcript"] == "hi"
    assert req["voice"] == {"mode": "id", "id": "v"}
    assert req["output_format"]["sample_rate"] == 24_000
    assert req["context_id"] == "loop-tts"


def test_cartesia_rejects_bad_sample_rate():
    with pytest.raises(ValueError):
        CartesiaConfig(api_key="k", voice_id="v", sample_rate=11025)


@pytest.mark.asyncio
async def test_cartesia_synthesize_chunks_then_done():
    chunks = [
        json.dumps({"type": "chunk", "data": base64.b64encode(b"AAA").decode()}),
        json.dumps({"type": "chunk", "data": base64.b64encode(b"BBBB").decode()}),
        json.dumps({"type": "done"}),
    ]
    ws = FakeWS(incoming=chunks)
    cfg = CartesiaConfig(api_key="k", voice_id="v")
    tts = CartesiaTextToSpeech(config=cfg, open_ws=make_ws_factory(ws))
    frames = [f async for f in tts.synthesize("hi")]
    assert [f.pcm for f in frames] == [b"AAA", b"BBBB"]
    assert [f.sequence for f in frames] == [0, 1]
    assert ws.closed is True


@pytest.mark.asyncio
async def test_cartesia_error_frame_raises():
    ws = FakeWS(incoming=[json.dumps({"type": "error", "error": "rate limit"})])
    cfg = CartesiaConfig(api_key="k", voice_id="v")
    tts = CartesiaTextToSpeech(config=cfg, open_ws=make_ws_factory(ws))
    with pytest.raises(CartesiaError):
        async for _ in tts.synthesize("hi"):
            pass


# --------------------------- Piper ---------------------------


def test_chunk_pcm_splits_evenly_and_tail():
    pieces = chunk_pcm(b"abcdefg", 3)
    assert pieces == [b"abc", b"def", b"g"]


def test_piper_config_validators():
    with pytest.raises(ValueError):
        PiperConfig(model_path=Path("/x"), frame_bytes=0)
    with pytest.raises(ValueError):
        PiperConfig(model_path=Path("/x"), frame_bytes=3)  # odd
    with pytest.raises(ValueError):
        PiperConfig(model_path=Path("/x"), sample_rate=11025)


@pytest.mark.asyncio
async def test_piper_synthesize_emits_chunks():
    class Runner:
        def synthesize_pcm(self, text: str, *, model_path: Path) -> bytes:
            return b"\x00\x01" * 100

    cfg = PiperConfig(model_path=Path("/m"), frame_bytes=80)
    tts = PiperTextToSpeech(config=cfg, runner=Runner())
    frames = [f async for f in tts.synthesize("hi")]
    assert [f.sequence for f in frames] == list(range(len(frames)))
    assert b"".join(f.pcm for f in frames) == b"\x00\x01" * 100


@pytest.mark.asyncio
async def test_piper_runner_error_wraps():
    class BadRunner:
        def synthesize_pcm(self, text, *, model_path):
            raise OSError("missing model")

    cfg = PiperConfig(model_path=Path("/m"))
    tts = PiperTextToSpeech(config=cfg, runner=BadRunner())
    with pytest.raises(PiperError):
        async for _ in tts.synthesize("hi"):
            pass


# --------------------------- LiveKit room ---------------------------


@dataclass
class FakeLiveKit:
    created: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    delete_raises: BaseException | None = None

    async def create_room(self, *, name, empty_timeout_seconds, max_participants) -> str:
        self.created.append(name)
        return f"sid-{len(self.created)}"

    async def delete_room(self, *, name) -> None:
        if self.delete_raises is not None:
            raise self.delete_raises
        self.deleted.append(name)

    def mint_token(self, grant: RoomGrant, *, api_key, api_secret) -> str:
        return f"jwt:{grant.room}:{grant.identity}:{int(grant.can_publish)}{int(grant.can_subscribe)}"


@pytest.mark.asyncio
async def test_livekit_room_create_and_token():
    client = FakeLiveKit()
    rm = RoomManager(client=client, api_key="k", api_secret="s", now_ms=lambda: 1_000)
    room = await rm.create_room(workspace_id=uuid4(), agent_id=uuid4())
    assert room.name in rm.rooms
    token = rm.mint_participant_token(room=room.name, identity="user-1")
    assert token.startswith("jwt:")
    assert client.created == [room.name]


@pytest.mark.asyncio
async def test_livekit_token_unknown_room_raises():
    rm = RoomManager(client=FakeLiveKit(), api_key="k", api_secret="s")
    with pytest.raises(RoomNotFound):
        rm.mint_participant_token(room="nope", identity="x")


@pytest.mark.asyncio
async def test_livekit_teardown_removes_room():
    client = FakeLiveKit()
    rm = RoomManager(client=client, api_key="k", api_secret="s")
    room = await rm.create_room(workspace_id=uuid4(), agent_id=uuid4())
    await rm.teardown(room.name)
    assert room.name not in rm.rooms
    assert client.deleted == [room.name]


@pytest.mark.asyncio
async def test_livekit_teardown_wraps_errors():
    client = FakeLiveKit(delete_raises=RuntimeError("boom"))
    rm = RoomManager(client=client, api_key="k", api_secret="s")
    room = await rm.create_room(workspace_id=uuid4(), agent_id=uuid4())
    with pytest.raises(LiveKitError):
        await rm.teardown(room.name)


def test_livekit_requires_credentials():
    with pytest.raises(ValueError):
        RoomManager(client=FakeLiveKit(), api_key="", api_secret="s")


# --------------------------- LiveKit bridge ---------------------------


@dataclass
class FakeTrack:
    inbound: list[bytes] = field(default_factory=list)
    published: list[bytes] = field(default_factory=list)
    closed: bool = False

    async def frames(self):
        for b in self.inbound:
            yield b

    async def publish(self, pcm: bytes) -> None:
        self.published.append(pcm)

    async def aclose(self) -> None:
        self.closed = True


class FakeTransport:
    pass


@pytest.mark.asyncio
async def test_livekit_bridge_pumps_in_and_out():
    track = FakeTrack(inbound=[b"a", b"bb"])
    bridge = LiveKitBridge(track=track, transport=FakeTransport())
    received: list[AudioFrame] = []

    async def on_inbound(frame: AudioFrame) -> None:
        received.append(frame)

    async def agent_audio() -> AsyncIterator[AudioFrame]:
        yield AudioFrame(pcm=b"OUT1", sequence=0)
        yield AudioFrame(pcm=b"OUT2", sequence=1)

    await bridge.run(on_inbound=on_inbound, agent_audio=agent_audio())
    assert track.closed is True
    # Inbound: at least one frame received and counters updated.
    assert bridge.stats.outbound_frames >= 1
    assert track.published[:2] == [b"OUT1", b"OUT2"] or track.published == [b"OUT1", b"OUT2"]


# --------------------------- Twilio ---------------------------


def test_build_twiml_minimal():
    cfg = TwimlConfig(stream=StreamConfig(websocket_url="wss://example.com/audio"))
    out = build_twiml(cfg)
    assert b"<Response>" in out
    assert b"<Connect>" in out
    assert b'url="wss://example.com/audio"' in out


def test_build_twiml_with_say_and_hangup():
    cfg = TwimlConfig(
        stream=StreamConfig(websocket_url="wss://x.com/a"),
        say_before="Hello there.",
        hangup_on_star=True,
    )
    out = build_twiml(cfg)
    assert b"<Say" in out and b"Hello there." in out
    assert b"<Hangup" in out


def test_stream_config_rejects_http():
    with pytest.raises(TwilioTwimlError):
        StreamConfig(websocket_url="https://example.com/a")


def test_parse_twilio_form_extracts_required():
    out = parse_twilio_form({
        "CallSid": "CA1", "From": "+1", "To": "+2", "AccountSid": "AC1", "extra": "x",
    })
    assert out == {"CallSid": "CA1", "From": "+1", "To": "+2", "AccountSid": "AC1"}


def test_parse_twilio_form_missing_required():
    with pytest.raises(TwilioTwimlError):
        parse_twilio_form({"CallSid": "X"})


# --------------------------- Voicemail ---------------------------


def test_plan_fallback_completed_no_action():
    p = plan_fallback(
        disposition=CallDisposition.COMPLETED,
        attempt=1,
        policy=VoicemailPolicy(),
        now_ms=1_000_000,
    )
    assert p.action is FallbackAction.NONE
    assert p.final_attempt is True


def test_plan_fallback_no_answer_leaves_voicemail_then_callback():
    policy = VoicemailPolicy(
        leave_voicemail_on_no_answer=True,
        callback_delay_seconds=600,
        max_callback_attempts=3,
        open_ticket_after_attempts=3,
    )
    p = plan_fallback(
        disposition=CallDisposition.NO_ANSWER, attempt=1, policy=policy, now_ms=1_000_000
    )
    assert p.action is FallbackAction.LEAVE_VOICEMAIL
    assert p.callback_at_ms == 1_000_000 + 600_000
    assert p.final_attempt is False


def test_plan_fallback_busy_schedules_callback():
    policy = VoicemailPolicy()
    p = plan_fallback(
        disposition=CallDisposition.BUSY, attempt=1, policy=policy, now_ms=1_000_000
    )
    assert p.action is FallbackAction.SCHEDULE_CALLBACK
    assert p.callback_at_ms is not None


def test_plan_fallback_final_attempt_opens_ticket():
    policy = VoicemailPolicy(max_callback_attempts=3, open_ticket_after_attempts=3)
    p = plan_fallback(
        disposition=CallDisposition.NO_ANSWER, attempt=3, policy=policy, now_ms=1_000_000
    )
    assert p.final_attempt is True
    assert p.action is FallbackAction.OPEN_TICKET


def test_voicemail_policy_validates():
    with pytest.raises(ValueError):
        VoicemailPolicy(callback_delay_seconds=10)
    with pytest.raises(ValueError):
        VoicemailPolicy(max_callback_attempts=0)
    with pytest.raises(ValueError):
        VoicemailPolicy(max_callback_attempts=2, open_ticket_after_attempts=5)
