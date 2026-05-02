"""S652 coverage for ASR/TTS websocket warm-up and pooling."""

from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import pytest
from loop_voice.asr_deepgram import DeepgramConfig, DeepgramSpeechToText, deepgram_url
from loop_voice.connection_pool import ConnectionPoolError, WarmWebSocketPool
from loop_voice.models import AudioFrame
from loop_voice.tts_elevenlabs import (
    ElevenLabsConfig,
    ElevenLabsTextToSpeech,
    elevenlabs_url,
)


def _str_list() -> list[str]:
    return []


def _bytes_list() -> list[bytes]:
    return []


@dataclass
class FakeWS:
    incoming: list[str] = field(default_factory=_str_list)
    sent_text: list[str] = field(default_factory=_str_list)
    sent_bytes: list[bytes] = field(default_factory=_bytes_list)
    closed: bool = False

    async def send_bytes(self, data: bytes) -> None:
        self.sent_bytes.append(data)

    async def send_text(self, text: str) -> None:
        self.sent_text.append(text)

    async def receive_text(self) -> str:
        if self.incoming:
            return self.incoming.pop(0)
        return ""

    async def aclose(self) -> None:
        self.closed = True


class DeepgramPoolWS(FakeWS):
    def __init__(self, incoming: list[str]) -> None:
        super().__init__(incoming=incoming)
        self._first_audio = asyncio.Event()
        self._close_stream = asyncio.Event()
        self._returned_transcript = False

    async def send_bytes(self, data: bytes) -> None:
        await super().send_bytes(data)
        self._first_audio.set()

    async def send_text(self, text: str) -> None:
        await super().send_text(text)
        if "CloseStream" in text:
            self._close_stream.set()

    async def receive_text(self) -> str:
        if not self._returned_transcript:
            await self._first_audio.wait()
            self._returned_transcript = True
            return await super().receive_text()
        await self._close_stream.wait()
        return ""


class FakeOpener:
    def __init__(self, sockets: list[FakeWS]) -> None:
        self._sockets = sockets
        self.calls: list[tuple[str, dict[str, str]]] = []

    async def __call__(self, url: str, headers: dict[str, str]) -> FakeWS:
        self.calls.append((url, headers))
        return self._sockets.pop(0)


def test_pool_rejects_zero_idle_timeout() -> None:
    with pytest.raises(ConnectionPoolError):
        WarmWebSocketPool(open_ws=FakeOpener([]), idle_timeout_ms=0)


@pytest.mark.asyncio
async def test_pool_prewarms_reuses_keepalives_and_closes_idle() -> None:
    now = 0
    raw = FakeWS()
    opener = FakeOpener([raw])
    pool = WarmWebSocketPool(
        open_ws=opener,
        idle_timeout_ms=100,
        keepalive_text="ping",
        now_ms=lambda: now,
    )

    await pool.prewarm("wss://voice.example/tts", {"Authorization": "token"})
    await pool.prewarm("wss://voice.example/tts", {"Authorization": "token"})
    assert pool.opened_count == 1

    await pool.keepalive()
    assert raw.sent_text == ["ping"]
    assert pool.keepalive_count == 1

    ws = await pool.open("wss://voice.example/tts", {"Authorization": "token"})
    assert pool.reused_count == 1
    await ws.aclose()

    now = 101
    await pool.close_idle()
    assert raw.closed is True
    assert pool.closed_idle_count == 1


@pytest.mark.asyncio
async def test_elevenlabs_uses_prewarmed_socket_from_pool() -> None:
    audio = base64.b64encode(b"PCM").decode()
    raw = FakeWS(incoming=[json.dumps({"audio": audio}), json.dumps({"isFinal": True})])
    opener = FakeOpener([raw])
    pool = WarmWebSocketPool(open_ws=opener)
    cfg = ElevenLabsConfig(api_key="k", voice_id="v")

    await pool.prewarm(elevenlabs_url(cfg), {"xi-api-key": cfg.api_key})
    tts = ElevenLabsTextToSpeech(config=cfg, open_ws=pool.open)
    frames = [frame async for frame in tts.synthesize("hello")]

    assert [frame.pcm for frame in frames] == [b"PCM"]
    assert pool.opened_count == 1
    assert pool.reused_count == 1
    assert raw.closed is False
    await pool.aclose()
    assert raw.closed is True


@pytest.mark.asyncio
async def test_deepgram_uses_prewarmed_socket_from_pool() -> None:
    raw = DeepgramPoolWS(
        incoming=[
            json.dumps(
                {
                    "is_final": True,
                    "channel": {"alternatives": [{"transcript": "hello", "confidence": 0.9}]},
                }
            ),
        ]
    )
    opener = FakeOpener([raw])
    pool = WarmWebSocketPool(open_ws=opener)
    cfg = DeepgramConfig(api_key="k")

    await pool.prewarm(deepgram_url(cfg), {"Authorization": "Token k"})
    stt = DeepgramSpeechToText(config=cfg, open_ws=pool.open)

    async def audio() -> AsyncIterator[AudioFrame]:
        yield AudioFrame(pcm=b"\x01\x00" * 800, sequence=0)

    transcripts = [transcript async for transcript in stt.transcribe(audio())]

    assert [transcript.text for transcript in transcripts] == ["hello"]
    assert raw.sent_bytes
    assert any("CloseStream" in msg for msg in raw.sent_text)
    assert pool.opened_count == 1
    assert pool.reused_count == 1
