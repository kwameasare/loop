"""Run the fixed S841 gateway semantic-cache hit-ratio eval."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from loop_gateway.cache_eval import MIN_HIT_RATIO, GatewayCacheEvalResult, run_gateway_cache_eval


def _write_report(output: Path, result: GatewayCacheEvalResult) -> None:
    payload = {
        "ts": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "regression_threshold": 0.10,
        "baseline_ref": "main",
    } | result.as_dict()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _exit_code(result: GatewayCacheEvalResult, min_hit_ratio: float) -> int:
    if not result.passed:
        print(
            f"gateway-cache-hit-ratio: {result.hit_ratio:.1%} below {min_hit_ratio:.1%}",
            file=sys.stderr,
        )
        return 2
    print(f"gateway-cache-hit-ratio: {result.hit_ratio:.1%} ({result.hits}/{result.requests})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("bench/results/gateway_cache_hit_ratio.json")
    )
    parser.add_argument("--min-hit-ratio", type=float, default=MIN_HIT_RATIO)
    args = parser.parse_args(argv)
    output = cast(Path, args.output)
    min_hit_ratio = cast(float, args.min_hit_ratio)
    result = asyncio.run(run_gateway_cache_eval(min_hit_ratio=min_hit_ratio))
    _write_report(output, result)
    return _exit_code(result, min_hit_ratio)


if __name__ == "__main__":
    raise SystemExit(main())
