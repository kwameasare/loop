"""S650 coverage for Deepgram ASR frame-level dispatch."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import pytest
from loop_voice.asr_deepgram import DeepgramConfig, DeepgramSpeechToText
from loop_voice.models import AudioFrame


@dataclass
class FirstTokenLatencyWS:
    sent_bytes: list[bytes] = field(default_factory=list)
    sent_text: list[str] = field(default_factory=list)
    closed: bool = False
    first_token_virtual_ms: int | None = None
    _first_audio: asyncio.Event = field(default_factory=asyncio.Event)
    _close_stream: asyncio.Event = field(default_factory=asyncio.Event)
    _returned_transcript: bool = False

    async def send_bytes(self, data: bytes) -> None:
        self.sent_bytes.append(data)
        if self.first_token_virtual_ms is None:
            self.first_token_virtual_ms = len(data) // 32
            self._first_audio.set()

    async def send_text(self, text: str) -> None:
        self.sent_text.append(text)
        self._close_stream.set()

    async def receive_text(self) -> str:
        if not self._returned_transcript:
            await self._first_audio.wait()
            self._returned_transcript = True
            return json.dumps(
                {
                    "is_final": False,
                    "channel": {"alternatives": [{"transcript": "hello", "confidence": 0.7}]},
                }
            )
        await self._close_stream.wait()
        return ""

    async def aclose(self) -> None:
        self.closed = True


def _ws_factory(ws: FirstTokenLatencyWS):
    async def _open(_url: str, _headers: dict[str, str]) -> FirstTokenLatencyWS:
        return ws

    return _open


async def _first_token_latency(dispatch_frame_ms: int) -> tuple[int, list[int]]:
    ws = FirstTokenLatencyWS()
    cfg = DeepgramConfig(api_key="k", dispatch_frame_ms=dispatch_frame_ms)
    stt = DeepgramSpeechToText(config=cfg, open_ws=_ws_factory(ws))

    async def audio() -> AsyncIterator[AudioFrame]:
        yield AudioFrame(pcm=b"\x01\x00" * 2_400, sequence=0)  # 150 ms @ 16kHz

    out = [t async for t in stt.transcribe(audio())]
    assert [t.text for t in out] == ["hello"]
    assert ws.closed is True
    assert ws.first_token_virtual_ms is not None
    return ws.first_token_virtual_ms, [len(chunk) for chunk in ws.sent_bytes]


def test_deepgram_config_rejects_oversized_dispatch_frame() -> None:
    with pytest.raises(ValueError):
        DeepgramConfig(api_key="k", dispatch_frame_ms=300)


@pytest.mark.asyncio
async def test_deepgram_dispatches_50ms_frames_for_lower_first_token_latency() -> None:
    fast_ms, fast_chunks = await _first_token_latency(dispatch_frame_ms=50)
    slow_ms, slow_chunks = await _first_token_latency(dispatch_frame_ms=150)

    assert fast_ms == 50
    assert slow_ms == 150
    assert fast_ms < slow_ms
    assert fast_chunks == [1_600, 1_600, 1_600]
    assert slow_chunks == [4_800]
