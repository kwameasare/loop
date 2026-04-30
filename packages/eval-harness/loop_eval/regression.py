"""Regression detector (S250).

Compares a fresh ``EvalReport`` against a stored baseline JSON and decides
whether the new run regressed the suite.

Default policy: a regression is declared when the **per-scorer mean score
drops by >= 5%** (relative) compared to baseline, or when previously-passing
samples now fail. The threshold is configurable so workspaces can tune
sensitivity without forking the harness.

The diff report is plain dataclasses so callers can render to TAP / JSON /
markdown without us picking a winner.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from loop_eval.models import EvalReport, Score


@dataclass(frozen=True)
class ScorerDelta:
    scorer: str
    baseline_mean: float
    current_mean: float
    delta: float
    relative_delta: float
    regressed: bool


@dataclass(frozen=True)
class SampleFlip:
    sample_id: str
    scorer: str
    was_passing: bool
    is_passing: bool


@dataclass(frozen=True)
class RegressionReport:
    regressed: bool
    threshold: float
    scorer_deltas: tuple[ScorerDelta, ...]
    flips: tuple[SampleFlip, ...]
    summary: str = field(default="")


def _means_by_scorer(scores: Iterable[Score]) -> dict[str, float]:
    sums: dict[str, float] = {}
    counts: dict[str, int] = {}
    for s in scores:
        sums[s.scorer] = sums.get(s.scorer, 0.0) + s.value
        counts[s.scorer] = counts.get(s.scorer, 0) + 1
    return {k: sums[k] / counts[k] for k in sums}


def _passed_by_pair(
    scores: Iterable[Score],
) -> dict[tuple[str, str], bool]:
    return {(s.scorer, s.sample_id): s.passed for s in scores}


def detect_regression(
    *,
    baseline: EvalReport,
    current: EvalReport,
    threshold: float = 0.05,
) -> RegressionReport:
    """Compare two reports and decide if ``current`` regressed."""

    if not 0.0 <= threshold < 1.0:
        raise ValueError("threshold must be in [0, 1)")

    baseline_means = _means_by_scorer(baseline.scores)
    current_means = _means_by_scorer(current.scores)

    deltas: list[ScorerDelta] = []
    for scorer, baseline_mean in baseline_means.items():
        current_mean = current_means.get(scorer, 0.0)
        delta = current_mean - baseline_mean
        rel = (delta / baseline_mean) if baseline_mean > 0 else 0.0
        regressed = (
            (baseline_mean > 0 and rel <= -threshold)
            or (baseline_mean == 0 and current_mean < 0)
        )
        deltas.append(
            ScorerDelta(
                scorer=scorer,
                baseline_mean=baseline_mean,
                current_mean=current_mean,
                delta=delta,
                relative_delta=rel,
                regressed=regressed,
            )
        )

    base_passed = _passed_by_pair(baseline.scores)
    cur_passed = _passed_by_pair(current.scores)
    flips: list[SampleFlip] = []
    for key, was in base_passed.items():
        is_now = cur_passed.get(key, False)
        if was and not is_now:
            flips.append(
                SampleFlip(
                    sample_id=key[1],
                    scorer=key[0],
                    was_passing=True,
                    is_passing=False,
                )
            )

    regressed = any(d.regressed for d in deltas) or bool(flips)
    summary_parts: list[str] = []
    if regressed:
        worst = min(deltas, key=lambda d: d.relative_delta, default=None)
        if worst is not None:
            summary_parts.append(
                f"worst scorer={worst.scorer} delta={worst.delta:+.3f} "
                f"({worst.relative_delta:+.1%})"
            )
        if flips:
            summary_parts.append(f"{len(flips)} previously-passing case(s) failing")
    else:
        summary_parts.append("no regression detected")
    return RegressionReport(
        regressed=regressed,
        threshold=threshold,
        scorer_deltas=tuple(sorted(deltas, key=lambda d: d.scorer)),
        flips=tuple(sorted(flips, key=lambda f: (f.scorer, f.sample_id))),
        summary="; ".join(summary_parts),
    )


def load_report(path: str | Path) -> EvalReport:
    p = Path(path)
    with p.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    # JSON has no tuple type; coerce lists to tuples for the strict model.
    if isinstance(data, dict):
        for key in ("runs", "scores"):
            if isinstance(data.get(key), list):
                data[key] = tuple(data[key])
    return EvalReport.model_validate(data, strict=False)


def dump_report(report: EvalReport, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        json.dump(report.model_dump(mode="json"), fh, indent=2, sort_keys=True)


def regression_to_dict(report: RegressionReport) -> Mapping[str, object]:
    """Plain-dict view safe to JSON-encode (for CI artefacts)."""

    return {
        "regressed": report.regressed,
        "threshold": report.threshold,
        "summary": report.summary,
        "scorer_deltas": [
            {
                "scorer": d.scorer,
                "baseline_mean": d.baseline_mean,
                "current_mean": d.current_mean,
                "delta": d.delta,
                "relative_delta": d.relative_delta,
                "regressed": d.regressed,
            }
            for d in report.scorer_deltas
        ],
        "flips": [
            {
                "sample_id": f.sample_id,
                "scorer": f.scorer,
                "was_passing": f.was_passing,
                "is_passing": f.is_passing,
            }
            for f in report.flips
        ],
    }


__all__ = [
    "RegressionReport",
    "SampleFlip",
    "ScorerDelta",
    "detect_regression",
    "dump_report",
    "load_report",
    "regression_to_dict",
]
