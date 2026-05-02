"""Run the S842 synthetic 1M-chunk KB retrieval benchmark."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from loop_kb_engine.perf_fixture import (
    DEFAULT_CHUNK_COUNT,
    DEFAULT_TOP_K,
    TARGET_P50_MS,
    SyntheticMillionChunkFixture,
)

DEFAULT_ITERATIONS = 120
QUERIES = (
    "refund policy enterprise plan",
    "saml workspace role mapping",
    "voice latency regional endpoint",
    "knowledge base document refresh",
)


@dataclass(frozen=True, slots=True)
class KBRetrievalPerfResult:
    name: str
    chunk_count: int
    iterations: int
    top_k: int
    p50_ms: float
    p95_ms: float
    target_p50_ms: float

    @property
    def passed(self) -> bool:
        return self.p50_ms < self.target_p50_ms

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return {
            "name": self.name,
            "chunk_count": self.chunk_count,
            "iterations": self.iterations,
            "top_k": self.top_k,
            "p50_ms": round(self.p50_ms, 3),
            "p95_ms": round(self.p95_ms, 3),
            "target_p50_ms": self.target_p50_ms,
            "passed": self.passed,
        }


def run_kb_retrieval_perf(
    *,
    iterations: int = DEFAULT_ITERATIONS,
    chunk_count: int = DEFAULT_CHUNK_COUNT,
    top_k: int = DEFAULT_TOP_K,
    target_p50_ms: float = TARGET_P50_MS,
) -> KBRetrievalPerfResult:
    if iterations <= 0:
        raise ValueError("iterations must be > 0")
    fixture = SyntheticMillionChunkFixture(chunk_count=chunk_count)
    samples_ms: list[float] = []
    for i in range(iterations):
        query = QUERIES[i % len(QUERIES)]
        start = time.perf_counter_ns()
        hits = fixture.search(query, top_k=top_k)
        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        if len(hits) != top_k:
            raise RuntimeError(f"expected {top_k} hits, got {len(hits)}")
        samples_ms.append(elapsed_ms)
    return KBRetrievalPerfResult(
        name="kb_retrieval_1m_chunks",
        chunk_count=chunk_count,
        iterations=iterations,
        top_k=top_k,
        p50_ms=statistics.median(samples_ms),
        p95_ms=statistics.quantiles(samples_ms, n=100)[94],
        target_p50_ms=target_p50_ms,
    )


def _write_report(output: Path, result: KBRetrievalPerfResult) -> None:
    payload = {
        "ts": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "baseline_ref": "main",
        "regression_threshold": 0.10,
    } | result.as_dict()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("bench/results/kb_retrieval_1m.json"))
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--target-p50-ms", type=float, default=TARGET_P50_MS)
    args = parser.parse_args(argv)

    target = cast(float, args.target_p50_ms)
    result = run_kb_retrieval_perf(iterations=cast(int, args.iterations), target_p50_ms=target)
    _write_report(cast(Path, args.output), result)
    if not result.passed:
        print(f"kb-retrieval: p50 {result.p50_ms:.3f}ms >= {target:.1f}ms", file=sys.stderr)
        return 2
    print(f"kb-retrieval: p50 {result.p50_ms:.3f}ms < {target:.1f}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
