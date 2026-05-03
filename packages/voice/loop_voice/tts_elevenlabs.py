"""ElevenLabs streaming TTS adapter (S363).

ElevenLabs streams MP3 / PCM frames over a websocket; we frame them
into Loop ``AudioFrame``s with monotonically-increasing sequence
numbers. Production uses Loop's real websocket opener, while tests and
connection pools can still inject a websocket factory.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

from loop_voice.asr_deepgram import AsyncWebSocket, WebSocketFactory
from loop_voice.models import AudioFrame
from loop_voice.ws_transport import open_provider_websocket


class ElevenLabsError(RuntimeError):
    """ElevenLabs synth failed (auth, throttle, dropped socket)."""


@dataclass(frozen=True, slots=True)
class ElevenLabsConfig:
    """Per-voice synthesis knobs."""

    api_key: str
    voice_id: str
    model_id: str = "eleven_turbo_v2_5"
    output_format: str = "pcm_16000"  # PCM 16kHz mono
    stability: float = 0.5
    similarity_boost: float = 0.75
    optimize_streaming_latency: int = 3  # 0..4

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("api_key required")
        if not self.voice_id:
            raise ValueError("voice_id required")
        if not 0.0 <= self.stability <= 1.0:
            raise ValueError("stability must be in [0,1]")
        if not 0.0 <= self.similarity_boost <= 1.0:
            raise ValueError("similarity_boost must be in [0,1]")
        if not 0 <= self.optimize_streaming_latency <= 4:
            raise ValueError("optimize_streaming_latency must be in [0..4]")


def elevenlabs_url(config: ElevenLabsConfig, *, base: str = "wss://api.elevenlabs.io") -> str:
    return (
        f"{base}/v1/text-to-speech/{config.voice_id}/stream-input?"
        f"model_id={config.model_id}&output_format={config.output_format}"
        f"&optimize_streaming_latency={config.optimize_streaming_latency}"
    )


@dataclass(slots=True)
class ElevenLabsTextToSpeech:
    """Streaming TTS over ElevenLabs websocket."""

    config: ElevenLabsConfig
    open_ws: WebSocketFactory | None = None
    base_url: str = "wss://api.elevenlabs.io"

    async def synthesize(self, text: str) -> AsyncIterator[AudioFrame]:
        url = elevenlabs_url(self.config, base=self.base_url)
        headers = {"xi-api-key": self.config.api_key}
        opener = self.open_ws or open_provider_websocket
        try:
            ws: AsyncWebSocket = await opener(url, headers)
        except Exception as exc:
            raise ElevenLabsError(f"ws open failed: {exc}") from exc

        # Init with voice settings.
        await ws.send_text(
            json.dumps(
                {
                    "text": " ",
                    "voice_settings": {
                        "stability": self.config.stability,
                        "similarity_boost": self.config.similarity_boost,
                    },
                }
            )
        )
        # Send the actual text in one chunk + close-stream sentinel.
        await ws.send_text(json.dumps({"text": text, "try_trigger_generation": True}))
        await ws.send_text(json.dumps({"text": ""}))

        sequence = 0
        try:
            while True:
                try:
                    raw = await ws.receive_text()
                except Exception as exc:
                    raise ElevenLabsError(f"recv failed: {exc}") from exc
                if not raw:
                    return
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise ElevenLabsError(f"non-json frame: {exc}") from exc
                audio_b64 = msg.get("audio")
                if audio_b64:
                    import base64

                    pcm = base64.b64decode(audio_b64)
                    yield AudioFrame(pcm=pcm, sequence=sequence)
                    sequence += 1
                if msg.get("isFinal"):
                    return
        finally:
            await ws.aclose()


__all__ = [
    "ElevenLabsConfig",
    "ElevenLabsError",
    "ElevenLabsTextToSpeech",
    "elevenlabs_url",
]
