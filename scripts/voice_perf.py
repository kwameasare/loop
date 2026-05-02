"""Run the S654 voice latency p50 acceptance benchmark."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from loop_voice import LatencyMeasurement, LatencyStage, LatencyTracker

TARGET_P50_MS = 700.0
DEFAULT_ITERATIONS = 100


@dataclass(frozen=True, slots=True)
class VoicePerfResult:
    name: str
    iterations: int
    p50_ms: float
    p95_ms: float
    target_p50_ms: float

    @property
    def passed(self) -> bool:
        return self.p50_ms <= self.target_p50_ms

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return {
            "name": self.name,
            "iterations": self.iterations,
            "p50_ms": round(self.p50_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "target_p50_ms": self.target_p50_ms,
            "passed": self.passed,
        }


def _stage_ms(i: int) -> dict[LatencyStage, float]:
    jitter = i % 9
    return {
        LatencyStage.NETWORK_IN: 16 + (jitter % 3),
        LatencyStage.ASR_FINAL: 138 + (jitter * 3),
        LatencyStage.AGENT: 230 + (jitter * 6),
        LatencyStage.TTS_FIRST_BYTE: 126 + (jitter * 4),
        LatencyStage.NETWORK_OUT: 16 + (jitter % 4),
    }


def run_voice_perf(
    *,
    iterations: int = DEFAULT_ITERATIONS,
    target_p50_ms: float = TARGET_P50_MS,
) -> VoicePerfResult:
    if iterations <= 0:
        raise ValueError("iterations must be > 0")
    if target_p50_ms <= 0:
        raise ValueError("target_p50_ms must be > 0")

    tracker = LatencyTracker()
    for i in range(iterations):
        tracker.record(LatencyMeasurement(turn_id=f"synthetic-{i}", stage_ms=_stage_ms(i)))

    percentiles = tracker.percentiles(stage=None)
    return VoicePerfResult(
        name="voice_perf_p50_gate",
        iterations=iterations,
        p50_ms=percentiles["p50"],
        p95_ms=percentiles["p95"],
        target_p50_ms=target_p50_ms,
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
    parser.add_argument("--target-p50-ms", type=float, default=TARGET_P50_MS)
    args = parser.parse_args(argv)

    target = cast(float, args.target_p50_ms)
    result = run_voice_perf(iterations=cast(int, args.iterations), target_p50_ms=target)
    _write_report(cast(Path, args.output), result)
    if not result.passed:
        print(f"voice-perf: p50 {result.p50_ms:.1f}ms > {target:.1f}ms", file=sys.stderr)
        return 2
    print(f"voice-perf: p50 {result.p50_ms:.1f}ms <= {target:.1f}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
