"""Cartesia (Sonic) streaming TTS adapter (S364).

Cartesia ships a Sonic model with very low TTFT; their websocket
protocol expects a JSON envelope per chunk with ``transcript`` text and
returns base64-encoded raw PCM. The shape is similar to ElevenLabs
but with a different framing on the wire.
"""

from __future__ import annotations

import base64
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from loop_voice.asr_deepgram import AsyncWebSocket
from loop_voice.models import AudioFrame


class CartesiaError(RuntimeError):
    """Cartesia synth failed."""


@dataclass(frozen=True, slots=True)
class CartesiaConfig:
    api_key: str
    voice_id: str
    model_id: str = "sonic-english"
    sample_rate: int = 16_000
    container: str = "raw"  # raw PCM
    encoding: str = "pcm_s16le"

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("api_key required")
        if not self.voice_id:
            raise ValueError("voice_id required")
        if self.sample_rate not in (8_000, 16_000, 22_050, 24_000, 44_100, 48_000):
            raise ValueError(f"unsupported sample_rate {self.sample_rate}")


def cartesia_url(config: CartesiaConfig, *, base: str = "wss://api.cartesia.ai") -> str:
    return f"{base}/tts/websocket?cartesia_version=2024-06-10"


def build_cartesia_request(config: CartesiaConfig, text: str) -> dict[str, Any]:
    """Build the JSON request body Cartesia expects on the WS."""
    return {
        "context_id": "loop-tts",
        "model_id": config.model_id,
        "transcript": text,
        "voice": {"mode": "id", "id": config.voice_id},
        "output_format": {
            "container": config.container,
            "encoding": config.encoding,
            "sample_rate": config.sample_rate,
        },
        "language": "en",
    }


@dataclass(slots=True)
class CartesiaTextToSpeech:
    config: CartesiaConfig
    open_ws: Any
    base_url: str = "wss://api.cartesia.ai"

    async def synthesize(self, text: str) -> AsyncIterator[AudioFrame]:
        url = cartesia_url(self.config, base=self.base_url)
        headers = {
            "X-API-Key": self.config.api_key,
            "Cartesia-Version": "2024-06-10",
        }
        try:
            ws: AsyncWebSocket = await self.open_ws(url, headers)
        except Exception as exc:
            raise CartesiaError(f"ws open failed: {exc}") from exc

        await ws.send_text(json.dumps(build_cartesia_request(self.config, text)))
        sequence = 0
        try:
            while True:
                try:
                    raw = await ws.receive_text()
                except Exception as exc:
                    raise CartesiaError(f"recv failed: {exc}") from exc
                if not raw:
                    return
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise CartesiaError(f"non-json frame: {exc}") from exc
                if msg.get("type") == "error":
                    raise CartesiaError(msg.get("error", "unknown"))
                if msg.get("type") == "chunk" and msg.get("data"):
                    pcm = base64.b64decode(msg["data"])
                    yield AudioFrame(pcm=pcm, sequence=sequence)
                    sequence += 1
                if msg.get("type") == "done":
                    return
        finally:
            await ws.aclose()


__all__ = [
    "CartesiaConfig",
    "CartesiaError",
    "CartesiaTextToSpeech",
    "build_cartesia_request",
    "cartesia_url",
]
