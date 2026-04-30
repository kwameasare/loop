"""Deepgram streaming ASR adapter (S361).

Loop never opens a Deepgram websocket directly. Production injects an
``AsyncWebSocket`` transport (httpx_ws or websockets); tests inject a
fake. The adapter handles:

* framing PCM ``AudioFrame``s into Deepgram's binary protocol,
* parsing JSON transcripts (partials + ``is_final`` + ``speech_final``),
* mapping language/model knobs to query params,
* surfacing typed errors so the failover layer (S367) can make a
  decision without inspecting message strings.
"""

from __future__ import annotations

import contextlib
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from loop_voice.models import AudioFrame, Transcript


class DeepgramError(RuntimeError):
    """Deepgram session failed (auth, dropped socket, malformed frame)."""


@runtime_checkable
class AsyncWebSocket(Protocol):
    """Subset of ``httpx_ws.AsyncWebSocketSession`` we depend on."""

    async def send_bytes(self, data: bytes) -> None: ...

    async def send_text(self, text: str) -> None: ...

    async def receive_text(self) -> str: ...

    async def aclose(self) -> None: ...


WebSocketFactory = Any  # async def (url, headers) -> AsyncWebSocket


@dataclass(frozen=True, slots=True)
class DeepgramConfig:
    """Session knobs. Defaults match prod config in HANDBOOK §voice."""

    api_key: str
    model: str = "nova-2-phonecall"
    language: str = "en-US"
    sample_rate: int = 16_000
    encoding: str = "linear16"
    interim_results: bool = True
    endpointing_ms: int = 250  # silence threshold for utterance end

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("api_key required")
        if self.sample_rate not in (8_000, 16_000, 24_000, 48_000):
            raise ValueError(f"unsupported sample_rate {self.sample_rate}")
        if self.endpointing_ms < 50:
            raise ValueError("endpointing_ms must be >=50")


def deepgram_url(config: DeepgramConfig, *, base: str = "wss://api.deepgram.com") -> str:
    """Build the Deepgram /v1/listen URL with config-driven query params."""
    params = [
        f"model={config.model}",
        f"language={config.language}",
        f"sample_rate={config.sample_rate}",
        f"encoding={config.encoding}",
        f"interim_results={'true' if config.interim_results else 'false'}",
        f"endpointing={config.endpointing_ms}",
    ]
    return f"{base}/v1/listen?" + "&".join(params)


def parse_deepgram_message(raw: str) -> Transcript | None:
    """Map a Deepgram JSON message to a ``Transcript`` (or None for keepalives)."""
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DeepgramError(f"non-json message: {exc}") from exc
    if msg.get("type") in ("Metadata", "SpeechStarted", "UtteranceEnd"):
        return None  # housekeeping, not a transcript
    channel = msg.get("channel") or {}
    alternatives = channel.get("alternatives") or []
    if not alternatives:
        return None
    alt = alternatives[0]
    text = alt.get("transcript", "")
    if not text:
        return None
    return Transcript(
        text=text,
        is_final=bool(msg.get("is_final", False)),
        confidence=float(alt.get("confidence", 0.0)),
    )


@dataclass(slots=True)
class DeepgramSpeechToText:
    """Streaming ASR backed by a caller-supplied websocket factory."""

    config: DeepgramConfig
    open_ws: Any  # async (url, headers) -> AsyncWebSocket
    base_url: str = "wss://api.deepgram.com"
    _ws: AsyncWebSocket | None = field(default=None, init=False)

    async def transcribe(
        self, audio: AsyncIterator[AudioFrame]
    ) -> AsyncIterator[Transcript]:
        url = deepgram_url(self.config, base=self.base_url)
        headers = {"Authorization": f"Token {self.config.api_key}"}
        try:
            ws = await self.open_ws(url, headers)
        except Exception as exc:
            raise DeepgramError(f"ws open failed: {exc}") from exc
        self._ws = ws

        async def _pump_audio() -> None:
            try:
                async for frame in audio:
                    await ws.send_bytes(frame.pcm)
                # Deepgram closes the stream on receipt of an empty binary frame.
                await ws.send_text(json.dumps({"type": "CloseStream"}))
            except Exception as exc:
                raise DeepgramError(f"audio pump failed: {exc}") from exc

        import asyncio

        pump = asyncio.create_task(_pump_audio())
        try:
            while True:
                try:
                    raw = await ws.receive_text()
                except Exception as exc:
                    raise DeepgramError(f"recv failed: {exc}") from exc
                if not raw:
                    return
                transcript = parse_deepgram_message(raw)
                if transcript is not None:
                    yield transcript
        finally:
            pump.cancel()
            with contextlib.suppress(asyncio.CancelledError, DeepgramError):
                await pump
            await ws.aclose()


__all__ = [
    "AsyncWebSocket",
    "DeepgramConfig",
    "DeepgramError",
    "DeepgramSpeechToText",
    "deepgram_url",
    "parse_deepgram_message",
]
