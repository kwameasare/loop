"""Fail when any committed perf report regresses p95 by 5% or more."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

DEFAULT_BASELINE = Path("bench/results/perf_7d_baseline.json")
DEFAULT_OUTPUT = Path("bench/results/perf_regression_budget.json")
type MetricResult = dict[str, bool | float | str]


def _load_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text()))


def _metric_p95_ms(payload: dict[str, Any], source: Path) -> float:
    p95: object | None = payload.get("p95_ms")
    stats: object | None = payload.get("stats")
    if p95 is None and isinstance(stats, dict):
        p95 = cast(dict[str, object], stats).get("p95_ms")
    if p95 is None:
        raise ValueError(f"{source} does not expose p95_ms")
    if isinstance(p95, bool) or not isinstance(p95, int | float | str):
        raise ValueError(f"{source} p95_ms must be numeric")
    value = float(p95)
    if value < 0:
        raise ValueError(f"{source} p95_ms must be non-negative")
    return value


def _resolve_source(raw: object) -> Path:
    path = Path(str(raw))
    return path if path.is_absolute() else Path.cwd() / path


def compare_budget(
    baseline_path: Path = DEFAULT_BASELINE,
    *,
    threshold_percent: float | None = None,
) -> tuple[dict[str, Any], list[MetricResult]]:
    baseline = _load_json(baseline_path)
    threshold = float(threshold_percent or baseline["max_p95_regression_percent"])
    metrics = cast(dict[str, dict[str, Any]], baseline["metrics"])
    results: list[MetricResult] = []
    for name, metric in sorted(metrics.items()):
        source = _resolve_source(metric["source"])
        baseline_p95 = float(metric["p95_ms"])
        if baseline_p95 <= 0:
            raise ValueError(f"{name} baseline p95_ms must be > 0")
        current_p95 = _metric_p95_ms(_load_json(source), source)
        regression = ((current_p95 - baseline_p95) / baseline_p95) * 100
        results.append(
            {
                "name": name,
                "source": str(metric["source"]),
                "baseline_p95_ms": round(baseline_p95, 3),
                "current_p95_ms": round(current_p95, 3),
                "regression_percent": round(regression, 3),
                "threshold_percent": threshold,
                "breached": regression >= threshold,
            }
        )
    return baseline, results


def write_report(output: Path, baseline: dict[str, Any], results: list[MetricResult]) -> None:
    breaches = [item for item in results if item["breached"] is True]
    payload = {
        "name": "perf_regression_budget",
        "ts": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "baseline_ref": "last_7_days",
        "window_days": int(baseline["window_days"]),
        "max_p95_regression_percent": float(baseline["max_p95_regression_percent"]),
        "passed": not breaches,
        "metrics": results,
        "breaches": breaches,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--threshold-percent", type=float)
    args = parser.parse_args(argv)

    baseline, results = compare_budget(
        cast(Path, args.baseline),
        threshold_percent=cast(float | None, args.threshold_percent),
    )
    write_report(cast(Path, args.output), baseline, results)
    breaches = [item for item in results if item["breached"] is True]
    if breaches:
        names = ", ".join(str(item["name"]) for item in breaches)
        print(f"perf-regression-budget: breached p95 budget for {names}", file=sys.stderr)
        return 2
    print(f"perf-regression-budget: {len(results)} p95 checks within budget")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
