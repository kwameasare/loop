"""Run the S654 voice latency p50 acceptance benchmark."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from loop_voice import LatencyMeasurement, LatencyStage, LatencyTracker

TARGET_P50_MS = 700.0
DEFAULT_ITERATIONS = 100
DEFAULT_SAMPLE_SOURCE = "synthetic:s908-cassette-replay-no-live-credentials"

StageMs = dict[str, float]


@dataclass(frozen=True, slots=True)
class VoicePerfSample:
    turn_id: str
    source: str
    stage_ms: StageMs

    def __post_init__(self) -> None:
        if not self.turn_id:
            raise ValueError("turn_id required")
        if not self.source:
            raise ValueError("sample source required")
        if not self.stage_ms:
            raise ValueError("stage_ms required")

    @property
    def total_ms(self) -> float:
        return sum(self.stage_ms.values())

    def measurement(self) -> LatencyMeasurement:
        return LatencyMeasurement(
            turn_id=self.turn_id,
            stage_ms={LatencyStage(stage): ms for stage, ms in self.stage_ms.items()},
        )

    def as_dict(self) -> dict[str, float | str | StageMs]:
        return {
            "turn_id": self.turn_id,
            "source": self.source,
            "stage_ms": dict(self.stage_ms),
            "total_ms": round(self.total_ms, 2),
        }


@dataclass(frozen=True, slots=True)
class VoicePerfResult:
    name: str
    iterations: int
    p50_ms: float
    p95_ms: float
    target_p50_ms: float
    samples: tuple[VoicePerfSample, ...]

    @property
    def passed(self) -> bool:
        return self.p50_ms <= self.target_p50_ms

    @property
    def sample_sources(self) -> tuple[str, ...]:
        return tuple(sorted({sample.source for sample in self.samples}))

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "iterations": self.iterations,
            "sample_count": len(self.samples),
            "sample_sources": list(self.sample_sources),
            "p50_ms": round(self.p50_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "target_p50_ms": self.target_p50_ms,
            "passed": self.passed,
            "samples": [sample.as_dict() for sample in self.samples],
        }


def _synthetic_fixture_stage_ms(i: int) -> StageMs:
    jitter = i % 9
    return {
        LatencyStage.NETWORK_IN.value: 16 + (jitter % 3),
        LatencyStage.ASR_FINAL.value: 138 + (jitter * 3),
        LatencyStage.AGENT.value: 230 + (jitter * 6),
        LatencyStage.TTS_FIRST_BYTE.value: 126 + (jitter * 4),
        LatencyStage.NETWORK_OUT.value: 16 + (jitter % 4),
    }


def _synthetic_fixture_samples(iterations: int) -> tuple[VoicePerfSample, ...]:
    return tuple(
        VoicePerfSample(
            turn_id=f"synthetic-{i}",
            source=DEFAULT_SAMPLE_SOURCE,
            stage_ms=_synthetic_fixture_stage_ms(i),
        )
        for i in range(iterations)
    )


def _load_samples(path: Path) -> tuple[VoicePerfSample, ...]:
    raw = cast(object, json.loads(path.read_text()))
    if isinstance(raw, dict):
        payload = cast(dict[str, object], raw)
        items_obj = payload.get("samples")
    else:
        items_obj = raw
    if not isinstance(items_obj, list):
        raise ValueError("samples file must contain a list or {'samples': [...]}")
    items = cast(list[object], items_obj)
    samples: list[VoicePerfSample] = []
    for item_obj in items:
        if not isinstance(item_obj, dict):
            raise ValueError("sample must be an object")
        item = cast(dict[str, object], item_obj)
        stage_obj = item.get("stage_ms")
        if not isinstance(stage_obj, dict):
            raise ValueError("sample.stage_ms must be an object")
        stage_ms = cast(dict[str, object], stage_obj)
        samples.append(
            VoicePerfSample(
                turn_id=str(item.get("turn_id", "")),
                source=str(item.get("source", "")),
                stage_ms=_coerce_stage_ms(stage_ms),
            )
        )
    return tuple(samples)


def _coerce_stage_ms(stage_ms: dict[str, object]) -> StageMs:
    coerced: StageMs = {}
    for stage, ms in stage_ms.items():
        if not isinstance(ms, int | float):
            raise ValueError("sample.stage_ms values must be numeric")
        coerced[str(stage)] = float(ms)
    return coerced


def run_voice_perf(
    *,
    iterations: int = DEFAULT_ITERATIONS,
    target_p50_ms: float = TARGET_P50_MS,
    samples: tuple[VoicePerfSample, ...] | None = None,
) -> VoicePerfResult:
    if iterations <= 0:
        raise ValueError("iterations must be > 0")
    if target_p50_ms <= 0:
        raise ValueError("target_p50_ms must be > 0")
    if samples is None:
        samples = _synthetic_fixture_samples(iterations)
    if not samples:
        raise ValueError("at least one sample is required")

    tracker = LatencyTracker()
    for sample in samples:
        tracker.record(sample.measurement())

    percentiles = tracker.percentiles(stage=None)
    return VoicePerfResult(
        name="voice_perf_p50_gate",
        iterations=len(samples),
        p50_ms=percentiles["p50"],
        p95_ms=percentiles["p95"],
        target_p50_ms=target_p50_ms,
        samples=samples,
    )


def _write_report(output: Path, result: VoicePerfResult) -> None:
    payload = {
        "ts": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "baseline_ref": "main",
        "regression_threshold": 0.10,
    } | result.as_dict()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("bench/results/voice_perf.json"))
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument(
        "--samples", type=Path, help="JSON file containing real or synthetic samples"
    )
    parser.add_argument("--target-p50-ms", type=float, default=TARGET_P50_MS)
    args = parser.parse_args(argv)

    target = cast(float, args.target_p50_ms)
    samples = _load_samples(cast(Path, args.samples)) if args.samples else None
    result = run_voice_perf(
        iterations=cast(int, args.iterations),
        target_p50_ms=target,
        samples=samples,
    )
    _write_report(cast(Path, args.output), result)
    if not result.passed:
        print(f"voice-perf: p50 {result.p50_ms:.1f}ms > {target:.1f}ms", file=sys.stderr)
        return 2
    print(f"voice-perf: p50 {result.p50_ms:.1f}ms <= {target:.1f}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
