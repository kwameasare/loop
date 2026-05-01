"""Turn-frame replay and regression-case helpers (S480-S487).

The production runtime writes every turn event to an append-only log subject.
This module keeps that seam intentionally small: a ``FrameLogSink`` Protocol
looks like the NATS log we will use in prod, while tests use
``InMemoryFrameLog``. Replay, diffing, and eval-case conversion are pure data
operations, so no network access is needed.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol

import yaml
from pydantic import BaseModel, ConfigDict, Field

from loop_eval.cassettes import CassetteEntry
from loop_eval.models import Sample


class TurnFrame(BaseModel):
    """One persisted frame emitted by a turn."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    turn_id: str = Field(min_length=1)
    seq: int = Field(ge=0)
    kind: str = Field(min_length=1)
    timestamp_ms: int = Field(ge=0)
    payload: dict[str, Any] = Field(default_factory=dict)
    cost_usd: float = Field(default=0.0, ge=0.0)
    latency_ms: float = Field(default=0.0, ge=0.0)


class RecordedTurn(BaseModel):
    """A replayable turn built from ordered frames."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    turn_id: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    frames: tuple[TurnFrame, ...]
    version: str = Field(min_length=1)
    metadata: dict[str, str] = Field(default_factory=dict)

    @property
    def total_cost_usd(self) -> float:
        return sum(frame.cost_usd for frame in self.frames)

    @property
    def total_latency_ms(self) -> float:
        return sum(frame.latency_ms for frame in self.frames)


class FrameDiff(BaseModel):
    """One divergent frame in a replay comparison."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    seq: int = Field(ge=0)
    kind: str = Field(min_length=1)
    expected: str | None = None
    actual: str | None = None
    detail: str = Field(min_length=1)


class ReplayDiffResult(BaseModel):
    """Result of comparing a baseline recording to a replay."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    byte_equal: bool
    diffs: tuple[FrameDiff, ...]
    expected_cost_usd: float = Field(ge=0.0)
    actual_cost_usd: float = Field(ge=0.0)
    expected_latency_ms: float = Field(ge=0.0)
    actual_latency_ms: float = Field(ge=0.0)
    cost_delta_usd: float
    latency_delta_ms: float
    cost_regressed: bool
    latency_regressed: bool

    @property
    def passed(self) -> bool:
        return (
            self.byte_equal
            and not self.cost_regressed
            and not self.latency_regressed
        )


class RegressionCasePullRequest(BaseModel):
    """Deterministic stand-in for the auto-PR opened by deploy-gate wiring."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str = Field(min_length=1)
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    yaml_text: str = Field(min_length=1)


class FrameLogSink(Protocol):
    """Append/read contract for the durable turn-frame log."""

    async def append(self, subject: str, line: str) -> None: ...

    async def read(self, subject: str) -> tuple[str, ...]: ...


@dataclass
class InMemoryFrameLog:
    """NATS-like log sink used by unit and integration tests."""

    lines_by_subject: dict[str, list[str]] = field(
        default_factory=lambda: defaultdict(list)
    )

    async def append(self, subject: str, line: str) -> None:
        self.lines_by_subject[subject].append(line)

    async def read(self, subject: str) -> tuple[str, ...]:
        return tuple(self.lines_by_subject.get(subject, ()))


def turn_subject(turn_id: str) -> str:
    """Return the canonical log subject for a turn."""

    if not turn_id:
        raise ValueError("turn_id must not be empty")
    return f"loop.turn.{turn_id}.frames"


def serialise_frame(frame: TurnFrame) -> str:
    """Encode a frame as deterministic JSONL."""

    return json.dumps(
        frame.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )


def parse_frame(line: str) -> TurnFrame:
    raw = line.strip()
    if not raw:
        raise ValueError("empty turn-frame line")
    return TurnFrame.model_validate(json.loads(raw))


class TurnFrameRecorder:
    """Append-only recorder for per-turn frames."""

    def __init__(self, sink: FrameLogSink, *, subject: str) -> None:
        self._sink = sink
        self.subject = subject

    async def record(self, frame: TurnFrame) -> None:
        await self._sink.append(self.subject, serialise_frame(frame))

    async def record_many(self, frames: Iterable[TurnFrame]) -> None:
        for frame in frames:
            await self.record(frame)


async def load_recorded_turn(
    sink: FrameLogSink,
    *,
    subject: str,
    turn_id: str,
    version: str,
    metadata: dict[str, str] | None = None,
) -> RecordedTurn:
    """Load and validate a recorded turn from the frame log."""

    frames = tuple(sorted((parse_frame(line) for line in await sink.read(subject)), key=lambda f: f.seq))
    for frame in frames:
        if frame.turn_id != turn_id:
            raise ValueError(
                f"subject {subject!r} contains frame for turn {frame.turn_id!r}"
            )
    return RecordedTurn(
        turn_id=turn_id,
        subject=subject,
        frames=frames,
        version=version,
        metadata=metadata or {},
    )


FrameTransform = Callable[[TurnFrame], TurnFrame | Awaitable[TurnFrame]]


class DeterministicTurnReplayer:
    """Replays a recording against a target version by substituting the gateway.

    ``transform`` is the deterministic test seam for "alternate version"
    behavior. Production wiring will adapt this shape to the gateway cassette.
    """

    async def replay(
        self,
        recording: RecordedTurn,
        *,
        target_version: str,
        transform: FrameTransform | None = None,
    ) -> RecordedTurn:
        frames: list[TurnFrame] = []
        for frame in recording.frames:
            next_frame = transform(frame) if transform is not None else frame
            if hasattr(next_frame, "__await__"):
                next_frame = await next_frame  # type: ignore[assignment]
            frames.append(next_frame)
        metadata = {**recording.metadata, "source_version": recording.version}
        return RecordedTurn(
            turn_id=recording.turn_id,
            subject=recording.subject,
            frames=tuple(frames),
            version=target_version,
            metadata=metadata,
        )


def diff_recordings(
    expected: RecordedTurn,
    actual: RecordedTurn,
    *,
    max_extra_cost_usd: float = 0.0,
    max_extra_latency_ms: float = 0.0,
) -> ReplayDiffResult:
    """Compare two recordings, including cost and latency regression gates."""

    diffs: list[FrameDiff] = []
    max_len = max(len(expected.frames), len(actual.frames))
    expected_lines = [serialise_frame(frame) for frame in expected.frames]
    actual_lines = [serialise_frame(frame) for frame in actual.frames]
    for seq in range(max_len):
        expected_line = expected_lines[seq] if seq < len(expected_lines) else None
        actual_line = actual_lines[seq] if seq < len(actual_lines) else None
        if expected_line == actual_line:
            continue
        frame = (
            expected.frames[seq]
            if seq < len(expected.frames)
            else actual.frames[seq]
        )
        detail = "frame payload differs"
        if expected_line is None:
            detail = "actual replay emitted an extra frame"
        elif actual_line is None:
            detail = "actual replay missed an expected frame"
        diffs.append(
            FrameDiff(
                seq=seq,
                kind=frame.kind,
                expected=expected_line,
                actual=actual_line,
                detail=detail,
            )
        )

    cost_delta = actual.total_cost_usd - expected.total_cost_usd
    latency_delta = actual.total_latency_ms - expected.total_latency_ms
    return ReplayDiffResult(
        byte_equal=len(diffs) == 0,
        diffs=tuple(diffs),
        expected_cost_usd=expected.total_cost_usd,
        actual_cost_usd=actual.total_cost_usd,
        expected_latency_ms=expected.total_latency_ms,
        actual_latency_ms=actual.total_latency_ms,
        cost_delta_usd=cost_delta,
        latency_delta_ms=latency_delta,
        cost_regressed=cost_delta > max_extra_cost_usd,
        latency_regressed=latency_delta > max_extra_latency_ms,
    )


def cassette_entry_to_sample(
    entry: CassetteEntry,
    *,
    sample_id: str | None = None,
) -> Sample:
    """Convert a gateway cassette row into an eval sample."""

    usage = {f"usage.{key}": str(value) for key, value in entry.usage.items()}
    return Sample(
        id=sample_id or f"cassette-{entry.request_key[:12]}",
        input=json.dumps(entry.request, sort_keys=True),
        expected=entry.response,
        metadata={
            "cassette_request_key": entry.request_key,
            "recorded_at_ms": str(entry.recorded_at_ms),
            **usage,
        },
    )


def sample_to_eval_case_yaml(sample: Sample, *, suite: str) -> str:
    """Render one eval-suite YAML case for the failed turn."""

    doc = {
        "suite": suite,
        "samples": [
            {
                "id": sample.id,
                "input": sample.input,
                "expected": sample.expected,
                "metadata": sample.metadata,
            }
        ],
    }
    return yaml.safe_dump(doc, sort_keys=True)


def regression_case_for_turn(
    turn: RecordedTurn,
    *,
    suite: str = "deploy-gate",
    sha: str,
) -> RegressionCasePullRequest:
    """Build the regression eval case that deploy-gate would auto-open."""

    final_text = ""
    if turn.frames:
        payload = turn.frames[-1].payload
        final_text = str(payload.get("text", payload.get("output", "")))
    sample = Sample(
        id=f"prod-failure-{turn.turn_id}",
        input=json.dumps(
            [frame.model_dump(mode="json") for frame in turn.frames],
            sort_keys=True,
        ),
        expected=final_text,
        metadata={
            "source": "prod-failure",
            "turn_id": turn.turn_id,
            "version": turn.version,
            **turn.metadata,
        },
    )
    yaml_text = sample_to_eval_case_yaml(sample, suite=suite)
    path = f"evals/regressions/{sha}.yml"
    return RegressionCasePullRequest(
        path=path,
        title=f"Add replay regression for turn {turn.turn_id}",
        body=f"Auto-added {turn.turn_id} to {suite}.",
        yaml_text=yaml_text,
    )


__all__ = [
    "DeterministicTurnReplayer",
    "FrameDiff",
    "FrameLogSink",
    "InMemoryFrameLog",
    "RecordedTurn",
    "RegressionCasePullRequest",
    "ReplayDiffResult",
    "TurnFrame",
    "TurnFrameRecorder",
    "cassette_entry_to_sample",
    "diff_recordings",
    "load_recorded_turn",
    "parse_frame",
    "regression_case_for_turn",
    "sample_to_eval_case_yaml",
    "serialise_frame",
    "turn_subject",
]
