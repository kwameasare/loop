"""S908 coverage for real voice provider websocket clients."""

from __future__ import annotations

import asyncio
import base64
import json
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from loop_voice import ws_transport
from loop_voice.asr_deepgram import DeepgramConfig, DeepgramError, DeepgramSpeechToText
from loop_voice.models import AudioFrame
from loop_voice.tts_elevenlabs import ElevenLabsConfig, ElevenLabsTextToSpeech

CASSETTES = Path(__file__).parent / "cassettes" / "voice"


def _bytes_list() -> list[bytes]:
    return []


def _str_list() -> list[str]:
    return []


def _wire_frame_list() -> list[str | bytes]:
    return []


def _load_cassette(name: str) -> dict[str, Any]:
    raw = yaml.safe_load((CASSETTES / name).read_text())
    assert isinstance(raw, dict)
    return cast(dict[str, Any], raw)


@dataclass
class CassetteWebSocket:
    incoming: list[str]
    wait_for_audio: bool = False
    sent_bytes: list[bytes] = field(default_factory=_bytes_list)
    sent_text: list[str] = field(default_factory=_str_list)
    closed: bool = False
    _first_audio: asyncio.Event = field(default_factory=asyncio.Event)
    _close_stream: asyncio.Event = field(default_factory=asyncio.Event)

    async def send_bytes(self, data: bytes) -> None:
        self.sent_bytes.append(data)
        self._first_audio.set()

    async def send_text(self, text: str) -> None:
        self.sent_text.append(text)
        if "CloseStream" in text:
            self._close_stream.set()

    async def receive_text(self) -> str:
        if self.wait_for_audio and not self._first_audio.is_set():
            await self._first_audio.wait()
        if not self.incoming:
            return ""
        frame = self.incoming.pop(0)
        if self.wait_for_audio and frame == "":
            await self._close_stream.wait()
        return frame

    async def aclose(self) -> None:
        self.closed = True


@dataclass
class CassetteOpener:
    cassette: dict[str, Any]
    wait_for_audio: bool = False
    ws: CassetteWebSocket | None = None
    headers_seen: dict[str, str] | None = None

    async def __call__(self, url: str, headers: dict[str, str]) -> CassetteWebSocket:
        request = cast(dict[str, Any], self.cassette["request"])
        assert url == request["url"]
        assert sorted(headers) == sorted(cast(list[str], request["header_names"]))
        for name, prefix in cast(dict[str, str], request["header_prefixes"]).items():
            assert headers[name].startswith(prefix)
        self.headers_seen = dict(headers)
        self.ws = CassetteWebSocket(
            incoming=list(cast(list[str], self.cassette["response_frames"])),
            wait_for_audio=self.wait_for_audio,
        )
        return self.ws


@dataclass
class ScriptedConnection:
    incoming: list[str | bytes]
    wait_for_binary: bool = False
    sent: list[str | bytes] = field(default_factory=_wire_frame_list)
    closed: bool = False
    _first_binary: asyncio.Event = field(default_factory=asyncio.Event)

    async def send(self, data: str | bytes) -> None:
        self.sent.append(data)
        if isinstance(data, bytes):
            self._first_binary.set()

    async def recv(self) -> str | bytes:
        if self.wait_for_binary and not self._first_binary.is_set():
            await self._first_binary.wait()
        if self.incoming:
            return self.incoming.pop(0)
        return ""

    async def close(self) -> None:
        self.closed = True


async def _single_audio_frame() -> AsyncIterator[AudioFrame]:
    yield AudioFrame(pcm=b"\x01\x00" * 160, sequence=0)


@pytest.mark.asyncio
async def test_deepgram_cassette_replay_frames_audio_and_close_stream() -> None:
    cassette = _load_cassette("deepgram_listen.yaml")
    opener = CassetteOpener(cassette=cassette, wait_for_audio=True)
    cfg = DeepgramConfig(api_key="dg-secret")
    stt = DeepgramSpeechToText(config=cfg, open_ws=opener)

    transcripts = [transcript async for transcript in stt.transcribe(_single_audio_frame())]

    assert [transcript.text for transcript in transcripts] == ["hello loop"]
    assert transcripts[0].is_final is True
    assert opener.headers_seen == {"Authorization": "Token dg-secret"}
    assert opener.ws is not None
    assert opener.ws.sent_bytes == [b"\x01\x00" * 160]
    assert json.loads(opener.ws.sent_text[-1]) == {"type": "CloseStream"}
    assert "dg-secret" not in (CASSETTES / "deepgram_listen.yaml").read_text()


@pytest.mark.asyncio
async def test_elevenlabs_cassette_replay_sends_streaming_protocol() -> None:
    cassette = _load_cassette("elevenlabs_stream_input.yaml")
    opener = CassetteOpener(cassette=cassette)
    cfg = ElevenLabsConfig(api_key="el-secret", voice_id="voice-cassette")
    tts = ElevenLabsTextToSpeech(config=cfg, open_ws=opener)

    frames = [frame async for frame in tts.synthesize("hello loop")]

    assert [frame.pcm for frame in frames] == [b"PCM_A", b"PCM_B"]
    assert opener.headers_seen == {"xi-api-key": "el-secret"}
    assert opener.ws is not None
    assert json.loads(opener.ws.sent_text[0])["text"] == " "
    assert json.loads(opener.ws.sent_text[1]) == {
        "text": "hello loop",
        "try_trigger_generation": True,
    }
    assert json.loads(opener.ws.sent_text[2]) == {"text": ""}
    assert "el-secret" not in (CASSETTES / "elevenlabs_stream_input.yaml").read_text()


@pytest.mark.asyncio
async def test_deepgram_default_opener_calls_websockets_with_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    conn = ScriptedConnection(
        incoming=[
            json.dumps(
                {
                    "is_final": True,
                    "channel": {"alternatives": [{"transcript": "real path", "confidence": 0.8}]},
                }
            ),
            "",
        ],
        wait_for_binary=True,
    )

    async def fake_connect(url: str, **kwargs: Any) -> ScriptedConnection:
        calls.append((url, dict(kwargs)))
        return conn

    monkeypatch.setattr(ws_transport, "websockets_connect", fake_connect)
    stt = DeepgramSpeechToText(config=DeepgramConfig(api_key="dg-live-ish"))

    transcripts = [transcript async for transcript in stt.transcribe(_single_audio_frame())]

    assert [transcript.text for transcript in transcripts] == ["real path"]
    assert calls[0][0].startswith("wss://api.deepgram.com/v1/listen?")
    assert calls[0][1]["additional_headers"] == {"Authorization": "Token dg-live-ish"}
    assert calls[0][1]["max_size"] is None
    assert conn.sent[0] == b"\x01\x00" * 160
    assert conn.closed is True


@pytest.mark.asyncio
async def test_elevenlabs_default_opener_calls_websockets_with_protocol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio = base64.b64encode(b"PCM").decode()
    calls: list[tuple[str, dict[str, Any]]] = []
    conn = ScriptedConnection(
        incoming=[json.dumps({"audio": audio}), json.dumps({"isFinal": True})]
    )

    async def fake_connect(url: str, **kwargs: Any) -> ScriptedConnection:
        calls.append((url, dict(kwargs)))
        return conn

    monkeypatch.setattr(ws_transport, "websockets_connect", fake_connect)
    tts = ElevenLabsTextToSpeech(
        config=ElevenLabsConfig(api_key="el-live-ish", voice_id="voice-live")
    )

    frames = [frame async for frame in tts.synthesize("hello")]

    assert [frame.pcm for frame in frames] == [b"PCM"]
    assert calls[0][0].startswith("wss://api.elevenlabs.io/v1/text-to-speech/voice-live/")
    assert calls[0][1]["additional_headers"] == {"xi-api-key": "el-live-ish"}
    assert json.loads(cast(str, conn.sent[1])) == {"text": "hello", "try_trigger_generation": True}
    assert conn.closed is True


@pytest.mark.asyncio
async def test_deepgram_default_opener_wraps_connect_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_connect(url: str, **kwargs: Any) -> ScriptedConnection:
        raise OSError("dns unavailable")

    monkeypatch.setattr(ws_transport, "websockets_connect", fake_connect)
    stt = DeepgramSpeechToText(config=DeepgramConfig(api_key="dg-live-ish"))

    with pytest.raises(DeepgramError, match="ws open failed"):
        async for _ in stt.transcribe(_single_audio_frame()):
            pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_deepgram_elevenlabs_round_trip() -> None:
    if os.getenv("LOOP_VOICE_LIVE_TESTS") != "1":
        pytest.skip("set LOOP_VOICE_LIVE_TESTS=1 to spend live voice provider quota")
    deepgram_key = os.getenv("LOOP_VOICE_DEEPGRAM_API_KEY") or os.getenv(
        "LOOP_CHANNEL_VOICE_DEEPGRAM_API_KEY"
    )
    elevenlabs_key = os.getenv("LOOP_VOICE_ELEVENLABS_API_KEY") or os.getenv(
        "LOOP_CHANNEL_VOICE_ELEVENLABS_API_KEY"
    )
    voice_id = os.getenv("LOOP_VOICE_ELEVENLABS_VOICE_ID")
    if not (deepgram_key and elevenlabs_key and voice_id):
        pytest.skip(
            "live voice test requires Deepgram key, ElevenLabs key, and ElevenLabs voice id"
        )

    tts = ElevenLabsTextToSpeech(config=ElevenLabsConfig(api_key=elevenlabs_key, voice_id=voice_id))
    frames = [frame async for frame in tts.synthesize("hello from loop")]
    assert frames

    async def audio() -> AsyncIterator[AudioFrame]:
        for frame in frames:
            yield frame

    stt = DeepgramSpeechToText(config=DeepgramConfig(api_key=deepgram_key))
    transcripts = [transcript async for transcript in stt.transcribe(audio())]
    assert any("hello" in transcript.text.lower() for transcript in transcripts)
