"""Whisper.cpp local ASR adapter (S362).

Whisper is the offline fallback when Deepgram is unreachable or the
workspace is on an air-gapped tier. It is *not* streaming — whisper.cpp
produces a transcript for a finite audio segment — so this adapter
buffers ``AudioFrame``s into utterances delimited by silence (or by an
explicit ``utterance_end`` from a VAD) and emits one final
``Transcript`` per utterance.

The actual ggml model invocation is hidden behind a ``WhisperRunner``
Protocol so tests don't shell out to whisper.cpp.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from loop_voice.models import AudioFrame, Transcript

DEFAULT_UTTERANCE_MAX_FRAMES = 1_000  # safety cap on a single buffer
DEFAULT_SILENCE_FRAMES = 25  # ~250 ms at 100 fps; tuned for telephony


class WhisperError(RuntimeError):
    """whisper.cpp invocation failed (model missing, runtime crash, ...)."""


@runtime_checkable
class WhisperRunner(Protocol):
    """Synchronous (blocking) runner. Production wraps subprocess to
    whisper.cpp; tests inject deterministic stubs."""

    def transcribe_pcm(self, pcm: bytes, *, language: str) -> tuple[str, float]: ...


@dataclass(frozen=True, slots=True)
class WhisperConfig:
    """Local model + decoding knobs."""

    model_path: Path
    language: str = "en"
    silence_frames: int = DEFAULT_SILENCE_FRAMES
    utterance_max_frames: int = DEFAULT_UTTERANCE_MAX_FRAMES

    def __post_init__(self) -> None:
        if self.silence_frames < 1:
            raise ValueError("silence_frames must be >=1")
        if self.utterance_max_frames < self.silence_frames:
            raise ValueError("utterance_max_frames must be >= silence_frames")


def _is_silent(frame: AudioFrame) -> bool:
    """Cheap energy check on signed 16-bit PCM little-endian."""
    pcm = frame.pcm
    if not pcm:
        return True
    # sum |sample| / N -> approximate average amplitude.
    # Avoid pulling numpy in here; voice is on the hot path.
    n = len(pcm) // 2
    if n == 0:
        return True
    total = 0
    for i in range(0, n * 2, 2):
        sample = int.from_bytes(pcm[i : i + 2], "little", signed=True)
        total += abs(sample)
    avg = total // n
    return avg < 200  # ~ -42 dBFS, safely below speech


@dataclass(slots=True)
class WhisperSpeechToText:
    """Buffer-then-decode ASR, suitable for offline / fallback use."""

    config: WhisperConfig
    runner: WhisperRunner

    async def transcribe(
        self, audio: AsyncIterator[AudioFrame]
    ) -> AsyncIterator[Transcript]:
        buffer: list[bytes] = []
        silence_run = 0
        async for frame in audio:
            buffer.append(frame.pcm)
            if _is_silent(frame):
                silence_run += 1
            else:
                silence_run = 0
            should_flush = (
                silence_run >= self.config.silence_frames and buffer
            ) or len(buffer) >= self.config.utterance_max_frames
            if should_flush:
                pcm = b"".join(buffer)
                buffer.clear()
                silence_run = 0
                if not pcm:
                    continue
                try:
                    text, conf = self.runner.transcribe_pcm(
                        pcm, language=self.config.language
                    )
                except Exception as exc:
                    raise WhisperError(f"runner crashed: {exc}") from exc
                if text.strip():
                    yield Transcript(text=text, is_final=True, confidence=conf)
        # Flush any tail buffer.
        if buffer:
            pcm = b"".join(buffer)
            try:
                text, conf = self.runner.transcribe_pcm(
                    pcm, language=self.config.language
                )
            except Exception as exc:
                raise WhisperError(f"runner crashed: {exc}") from exc
            if text.strip():
                yield Transcript(text=text, is_final=True, confidence=conf)


__all__ = [
    "DEFAULT_SILENCE_FRAMES",
    "DEFAULT_UTTERANCE_MAX_FRAMES",
    "WhisperConfig",
    "WhisperError",
    "WhisperRunner",
    "WhisperSpeechToText",
]
