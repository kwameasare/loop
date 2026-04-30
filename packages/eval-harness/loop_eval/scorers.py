"""Built-in scorers.

Each scorer is a sync function ``(Sample, Run) -> Score``. The
`llm_judge` scorer accepts a synchronous ``JudgeFn`` so callers can
plug in any LLM (or a deterministic fake in tests). Async judging
is left to a future iteration.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any, Protocol

from loop_eval.models import Run, Sample


class Scorer(Protocol):
    name: str

    def __call__(self, sample: Sample, run: Run) -> object: ...


# A judge takes (input, expected, output) and returns a 0..1 float +
# rationale string. Test fakes can ignore the LLM and grade by hand.
JudgeFn = Callable[[str, str | None, str], tuple[float, str]]


def _score(
    *,
    name: str,
    sample: Sample,
    value: float,
    threshold: float,
    detail: str,
) -> object:
    # Deferred import keeps `models` and `scorers` independent.
    from loop_eval.models import Score

    return Score(
        scorer=name,
        sample_id=sample.id,
        value=max(0.0, min(1.0, value)),
        passed=value >= threshold,
        detail=detail,
    )


def exact_match(sample: Sample, run: Run) -> object:
    expected = sample.expected or ""
    ok = run.output.strip() == expected.strip()
    return _score(
        name="exact_match",
        sample=sample,
        value=1.0 if ok else 0.0,
        threshold=1.0,
        detail=("match" if ok else "mismatch"),
    )


exact_match.name = "exact_match"  # type: ignore[attr-defined]


def regex_match(pattern: str, *, threshold: float = 1.0) -> Scorer:
    """Returns a scorer that matches ``pattern`` against ``run.output``."""
    compiled = re.compile(pattern)

    def scorer(sample: Sample, run: Run) -> object:
        ok = compiled.search(run.output) is not None
        return _score(
            name="regex_match",
            sample=sample,
            value=1.0 if ok else 0.0,
            threshold=threshold,
            detail=f"pattern={pattern!r} ok={ok}",
        )

    scorer.name = "regex_match"  # type: ignore[attr-defined]
    return scorer  # type: ignore[return-value]


def json_schema_scorer(required_keys: tuple[str, ...]) -> Scorer:
    """Pass if ``run.output`` is JSON containing every required key."""

    def scorer(sample: Sample, run: Run) -> object:
        try:
            data: Any = json.loads(run.output)
        except json.JSONDecodeError as exc:
            return _score(
                name="json_schema",
                sample=sample,
                value=0.0,
                threshold=1.0,
                detail=f"invalid json: {exc.msg}",
            )
        if not isinstance(data, dict):
            return _score(
                name="json_schema",
                sample=sample,
                value=0.0,
                threshold=1.0,
                detail="json is not an object",
            )
        missing = [k for k in required_keys if k not in data]
        ok = not missing
        return _score(
            name="json_schema",
            sample=sample,
            value=1.0 if ok else 0.0,
            threshold=1.0,
            detail=("ok" if ok else f"missing keys: {missing}"),
        )

    scorer.name = "json_schema"  # type: ignore[attr-defined]
    return scorer  # type: ignore[return-value]


def llm_judge(judge: JudgeFn, *, threshold: float = 0.7) -> Scorer:
    """Wraps a `JudgeFn`. The judge returns ``(score in [0,1], rationale)``."""

    def scorer(sample: Sample, run: Run) -> object:
        value, rationale = judge(sample.input, sample.expected, run.output)
        return _score(
            name="llm_judge",
            sample=sample,
            value=value,
            threshold=threshold,
            detail=rationale,
        )

    scorer.name = "llm_judge"  # type: ignore[attr-defined]
    return scorer  # type: ignore[return-value]


def latency_scorer(*, max_ms: float) -> Scorer:
    """Pass if ``run.latency_ms <= max_ms``. Score = 1 - excess/max_ms."""
    if max_ms <= 0:
        raise ValueError("max_ms must be positive")

    def scorer(sample: Sample, run: Run) -> object:
        excess = max(0.0, run.latency_ms - max_ms)
        value = max(0.0, 1.0 - excess / max_ms)
        return _score(
            name="latency",
            sample=sample,
            value=value,
            threshold=1.0,
            detail=f"latency={run.latency_ms:.1f}ms budget={max_ms:.1f}ms",
        )

    scorer.name = "latency"  # type: ignore[attr-defined]
    return scorer  # type: ignore[return-value]


def cost_scorer(*, max_usd: float) -> Scorer:
    """Pass if ``run.cost_usd <= max_usd``."""
    if max_usd <= 0:
        raise ValueError("max_usd must be positive")

    def scorer(sample: Sample, run: Run) -> object:
        excess = max(0.0, run.cost_usd - max_usd)
        value = max(0.0, 1.0 - excess / max_usd)
        return _score(
            name="cost",
            sample=sample,
            value=value,
            threshold=1.0,
            detail=f"cost=${run.cost_usd:.4f} budget=${max_usd:.4f}",
        )

    scorer.name = "cost"  # type: ignore[attr-defined]
    return scorer  # type: ignore[return-value]


__all__ = [
    "JudgeFn",
    "Scorer",
    "cost_scorer",
    "exact_match",
    "json_schema_scorer",
    "latency_scorer",
    "llm_judge",
    "regex_match",
]
