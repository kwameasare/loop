"""Run the S843 tool-host warm-start benchmark."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from loop_tool_host.warm_start_bench import TARGET_P95_MS, run_warm_start_bench


def _write_report(output: Path, payload: dict[str, bool | float | int | str]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("bench/results/tool_host_warm_start.json")
    )
    parser.add_argument("--iterations", type=int, default=80)
    parser.add_argument("--target-p95-ms", type=float, default=TARGET_P95_MS)
    args = parser.parse_args(argv)
    target = cast(float, args.target_p95_ms)
    result = asyncio.run(
        run_warm_start_bench(iterations=cast(int, args.iterations), target_p95_ms=target)
    )
    payload = {
        "ts": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "baseline_ref": "main",
        "regression_threshold": 0.10,
    } | result.as_dict()
    _write_report(cast(Path, args.output), payload)
    if not result.passed:
        print(f"tool-host-warm-start: p95 {result.p95_ms}ms >= {target}ms", file=sys.stderr)
        return 2
    print(f"tool-host-warm-start: p95 {result.p95_ms}ms < {target}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
