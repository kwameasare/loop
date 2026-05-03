"""Deepgram streaming ASR adapter (S361).

Loop opens a Deepgram websocket through the production ``websockets``
transport by default. Callers can still inject an ``AsyncWebSocket``
factory for connection pooling or cassette tests. The adapter handles:

* framing PCM ``AudioFrame``s into Deepgram's binary protocol,
* parsing JSON transcripts (partials + ``is_final`` + ``speech_final``),
* mapping language/model knobs to query params,
* surfacing typed errors so the failover layer (S367) can make a
  decision without inspecting message strings.
"""

from __future__ import annotations

import contextlib
import json
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from dataclasses import dataclass, field
from typing import Any, Protocol, cast, runtime_checkable

from loop_voice.models import AudioFrame, Transcript
from loop_voice.ws_transport import open_provider_websocket


class DeepgramError(RuntimeError):
    """Deepgram session failed (auth, dropped socket, malformed frame)."""


@runtime_checkable
class AsyncWebSocket(Protocol):
    """Subset of ``httpx_ws.AsyncWebSocketSession`` we depend on."""

    async def send_bytes(self, data: bytes) -> None: ...

    async def send_text(self, text: str) -> None: ...

    async def receive_text(self) -> str: ...

    async def aclose(self) -> None: ...


WebSocketFactory = Callable[[str, dict[str, str]], Awaitable[AsyncWebSocket]]


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
    dispatch_frame_ms: int = 50  # send ASR audio in low-latency slices

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("api_key required")
        if self.sample_rate not in (8_000, 16_000, 24_000, 48_000):
            raise ValueError(f"unsupported sample_rate {self.sample_rate}")
        if self.endpointing_ms < 50:
            raise ValueError("endpointing_ms must be >=50")
        if not 10 <= self.dispatch_frame_ms <= self.endpointing_ms:
            raise ValueError("dispatch_frame_ms must be between 10 and endpointing_ms")


def _dispatch_frame_bytes(config: DeepgramConfig) -> int:
    # linear16 mono = 2 bytes/sample. DeepgramConfig pins encoding to linear16 today.
    return max(2, config.sample_rate * 2 * config.dispatch_frame_ms // 1000)


def _iter_dispatch_chunks(pcm: bytes, chunk_bytes: int) -> Iterator[bytes]:
    for start in range(0, len(pcm), chunk_bytes):
        chunk = pcm[start : start + chunk_bytes]
        if chunk:
            yield chunk


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
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DeepgramError(f"non-json message: {exc}") from exc
    if not isinstance(parsed, dict):
        raise DeepgramError("message is not a json object")
    msg = cast(dict[str, Any], parsed)
    if msg.get("type") in ("Metadata", "SpeechStarted", "UtteranceEnd"):
        return None  # housekeeping, not a transcript
    channel = msg.get("channel")
    if not isinstance(channel, dict):
        return None
    channel = cast(dict[str, Any], channel)
    alternatives_obj = channel.get("alternatives")
    if not isinstance(alternatives_obj, list) or not alternatives_obj:
        return None
    alternatives = cast(list[Any], alternatives_obj)
    alt = alternatives[0]
    if not isinstance(alt, dict):
        return None
    alt = cast(dict[str, Any], alt)
    text = alt.get("transcript", "")
    if not isinstance(text, str) or not text:
        return None
    confidence = alt.get("confidence", 0.0)
    if not isinstance(confidence, int | float):
        confidence = 0.0
    return Transcript(
        text=text,
        is_final=bool(msg.get("is_final", False)),
        confidence=float(confidence),
    )


@dataclass(slots=True)
class DeepgramSpeechToText:
    """Streaming ASR backed by Deepgram's websocket API."""

    config: DeepgramConfig
    open_ws: WebSocketFactory | None = None
    base_url: str = "wss://api.deepgram.com"
    _ws: AsyncWebSocket | None = field(default=None, init=False)

    async def transcribe(self, audio: AsyncIterator[AudioFrame]) -> AsyncIterator[Transcript]:
        url = deepgram_url(self.config, base=self.base_url)
        headers = {"Authorization": f"Token {self.config.api_key}"}
        opener = self.open_ws or open_provider_websocket
        try:
            ws = await opener(url, headers)
        except Exception as exc:
            raise DeepgramError(f"ws open failed: {exc}") from exc
        self._ws = ws

        async def _pump_audio() -> None:
            chunk_bytes = _dispatch_frame_bytes(self.config)
            try:
                async for frame in audio:
                    for chunk in _iter_dispatch_chunks(frame.pcm, chunk_bytes):
                        await ws.send_bytes(chunk)
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
    "WebSocketFactory",
    "deepgram_url",
    "parse_deepgram_message",
]
