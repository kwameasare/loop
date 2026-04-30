"""Per-stage voice tracing for the ASR → LLM → TTS pipeline (S370).

Every voice turn passes through three asynchronous stages whose
latency contributes to the call's end-to-end budget. We need:

1. A span per stage, with attributes that surface ``provider``,
   ``model`` (when applicable), ``audio_ms`` (input or output), and
   ``first_byte_ms`` (time-to-first-token-or-frame).
2. The three spans linked under a single voice-turn parent so the
   trace UI renders a clean three-bar waterfall.
3. Independence from the OTel SDK at unit-test time. The recorder
   is a Protocol so production wires the real exporter and tests
   wire :class:`InMemoryStageRecorder`.

Spans are *attributes-only*; no sampling, batching, or context
propagation lives in this module — those are owned by
:mod:`loop_runtime.trace_correlation` (S408).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from enum import StrEnum
from types import TracebackType
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "InMemoryStageRecorder",
    "StageKind",
    "StageRecorder",
    "StageSpan",
    "VoicePipelineTracer",
    "VoiceTurnTrace",
]


class StageKind(StrEnum):
    ASR = "asr"
    LLM = "llm"
    TTS = "tts"


class StageSpan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    kind: StageKind
    provider: str = Field(min_length=1)
    model: str | None = None
    started_at_ms: int = Field(ge=0)
    ended_at_ms: int = Field(ge=0)
    first_byte_ms: int | None = Field(default=None, ge=0)
    audio_ms: int | None = Field(default=None, ge=0)
    error: str | None = None

    @property
    def duration_ms(self) -> int:
        return self.ended_at_ms - self.started_at_ms

    def to_otel_attrs(self) -> dict[str, str | int]:
        attrs: dict[str, str | int] = {
            "loop.voice.stage": self.kind.value,
            "loop.voice.provider": self.provider,
            "loop.voice.duration_ms": self.duration_ms,
        }
        if self.model is not None:
            attrs["loop.voice.model"] = self.model
        if self.first_byte_ms is not None:
            attrs["loop.voice.first_byte_ms"] = self.first_byte_ms
        if self.audio_ms is not None:
            attrs["loop.voice.audio_ms"] = self.audio_ms
        if self.error is not None:
            attrs["loop.voice.error"] = self.error
        return attrs


class VoiceTurnTrace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    workspace_id: UUID
    call_id: UUID
    turn_id: UUID
    spans: tuple[StageSpan, ...]

    def end_to_end_ms(self) -> int:
        if not self.spans:
            return 0
        return max(s.ended_at_ms for s in self.spans) - min(
            s.started_at_ms for s in self.spans
        )


class StageRecorder(Protocol):
    def record(self, span: StageSpan) -> None: ...


class InMemoryStageRecorder:
    def __init__(self) -> None:
        self.spans: list[StageSpan] = []

    def record(self, span: StageSpan) -> None:
        self.spans.append(span)


class VoicePipelineTracer:
    """Stateful tracer for a single voice turn.

    Usage::

        tracer = VoicePipelineTracer(workspace_id, call_id, turn_id, recorder)
        with tracer.stage(StageKind.ASR, provider="deepgram", model="nova-3") as s:
            ...
            s.first_byte_ms = 80
            s.audio_ms = 1500

    On exit, an immutable :class:`StageSpan` is built and forwarded
    to the recorder. ``finalise()`` returns the assembled
    :class:`VoiceTurnTrace`.
    """

    def __init__(
        self,
        *,
        workspace_id: UUID,
        call_id: UUID,
        turn_id: UUID,
        recorder: StageRecorder,
        clock_ms: Callable[[], int] | None = None,
    ) -> None:
        self._workspace_id = workspace_id
        self._call_id = call_id
        self._turn_id = turn_id
        self._recorder = recorder
        self._clock = clock_ms or _wall_clock_ms
        self._spans: list[StageSpan] = []

    def stage(self, kind: StageKind, *, provider: str, model: str | None = None) -> _StageContext:
        return _StageContext(self, kind=kind, provider=provider, model=model)

    @property
    def spans(self) -> Sequence[StageSpan]:
        return tuple(self._spans)

    def finalise(self) -> VoiceTurnTrace:
        return VoiceTurnTrace(
            workspace_id=self._workspace_id,
            call_id=self._call_id,
            turn_id=self._turn_id,
            spans=tuple(self._spans),
        )

    # --- internal ---

    def _now_ms(self) -> int:
        return self._clock()

    def _commit(self, span: StageSpan) -> None:
        self._spans.append(span)
        self._recorder.record(span)


class _StageContext:
    """Mutable scratch object yielded by ``with tracer.stage(...)``."""

    def __init__(
        self,
        tracer: VoicePipelineTracer,
        *,
        kind: StageKind,
        provider: str,
        model: str | None,
    ) -> None:
        self._tracer = tracer
        self._kind = kind
        self._provider = provider
        self._model = model
        self._started: int = 0
        self.first_byte_ms: int | None = None
        self.audio_ms: int | None = None
        self.error: str | None = None

    def __enter__(self) -> _StageContext:
        self._started = self._tracer._now_ms()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        ended = self._tracer._now_ms()
        if exc is not None and self.error is None:
            self.error = f"{type(exc).__name__}: {exc}"
        span = StageSpan(
            kind=self._kind,
            provider=self._provider,
            model=self._model,
            started_at_ms=self._started,
            ended_at_ms=ended,
            first_byte_ms=self.first_byte_ms,
            audio_ms=self.audio_ms,
            error=self.error,
        )
        self._tracer._commit(span)
        return False  # never swallow


def _wall_clock_ms() -> int:
    return time.monotonic_ns() // 1_000_000
