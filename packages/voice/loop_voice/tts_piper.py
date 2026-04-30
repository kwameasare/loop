"""Piper local TTS adapter (S365).

Piper ships a CLI ``piper`` that reads text on stdin and writes raw
16-bit PCM on stdout. Loop's adapter wraps a ``PiperRunner`` Protocol
that production fills in with subprocess and tests stub with a
deterministic byte map.

Piper is not streaming inside a single utterance, but the CLI is fast
enough on commodity CPUs that we treat it as "single-blob TTS" — the
adapter chunks the resulting PCM into fixed-size ``AudioFrame``s so
the downstream transport can paginate normally.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from loop_voice.models import AudioFrame

DEFAULT_FRAME_BYTES = 640  # 20 ms at 16 kHz, 16-bit mono


class PiperError(RuntimeError):
    """Piper invocation failed (model missing, runtime crash)."""


@runtime_checkable
class PiperRunner(Protocol):
    """Synchronous (blocking) text→PCM runner."""

    def synthesize_pcm(self, text: str, *, model_path: Path) -> bytes: ...


@dataclass(frozen=True, slots=True)
class PiperConfig:
    model_path: Path
    sample_rate: int = 22_050  # piper default
    frame_bytes: int = DEFAULT_FRAME_BYTES

    def __post_init__(self) -> None:
        if self.frame_bytes <= 0 or self.frame_bytes % 2:
            raise ValueError("frame_bytes must be positive and even")
        if self.sample_rate not in (8_000, 16_000, 22_050, 24_000, 44_100, 48_000):
            raise ValueError(f"unsupported sample_rate {self.sample_rate}")


def chunk_pcm(pcm: bytes, frame_bytes: int) -> list[bytes]:
    """Split a PCM blob into fixed-size frames; the last may be shorter."""
    if frame_bytes <= 0:
        raise ValueError("frame_bytes must be positive")
    return [pcm[i : i + frame_bytes] for i in range(0, len(pcm), frame_bytes)]


@dataclass(slots=True)
class PiperTextToSpeech:
    config: PiperConfig
    runner: PiperRunner

    async def synthesize(self, text: str) -> AsyncIterator[AudioFrame]:
        try:
            pcm = self.runner.synthesize_pcm(text, model_path=self.config.model_path)
        except Exception as exc:
            raise PiperError(f"runner crashed: {exc}") from exc
        if not pcm:
            return
        for sequence, chunk in enumerate(chunk_pcm(pcm, self.config.frame_bytes)):
            yield AudioFrame(pcm=chunk, sequence=sequence)


__all__ = [
    "DEFAULT_FRAME_BYTES",
    "PiperConfig",
    "PiperError",
    "PiperRunner",
    "PiperTextToSpeech",
    "chunk_pcm",
]
