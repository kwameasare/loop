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

from loop_eval.models import Run, Sample, ToolInvocation


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
    "bleu_scorer",
    "cost_scorer",
    "exact_match",
    "json_schema_scorer",
    "latency_scorer",
    "llm_judge",
    "regex_match",
    "rouge_l",
    "tool_call_match",
]


# --------------------------------------------------------------------------- #
# S242 -- ROUGE-L and BLEU scorers (no external deps).
# --------------------------------------------------------------------------- #


def _tokenise(text: str) -> list[str]:
    return [t for t in re.findall(r"[A-Za-z0-9']+", text.lower()) if t]


def _lcs_length(a: list[str], b: list[str]) -> int:
    if not a or not b:
        return 0
    # Two-row DP keeps memory O(min(len(a), len(b))).
    if len(a) < len(b):
        a, b = b, a
    prev = [0] * (len(b) + 1)
    for tok_a in a:
        curr = [0] * (len(b) + 1)
        for j, tok_b in enumerate(b, start=1):
            if tok_a == tok_b:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev = curr
    return prev[-1]


def rouge_l(*, threshold: float = 0.5) -> Scorer:
    """ROUGE-L F1 score (longest common subsequence) on tokenised output.

    Returns 0.0 when ``sample.expected`` is missing -- callers shouldn't be
    using this scorer without a reference. The implementation is a faithful
    F1 of LCS-based precision/recall, matching the canonical ROUGE-L
    definition. We avoid the ``rouge_score`` package because pulling in a
    300+ line scorer dependency is overkill.
    """

    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in [0, 1]")

    def scorer(sample: Sample, run: Run) -> object:
        ref = _tokenise(sample.expected or "")
        cand = _tokenise(run.output)
        if not ref or not cand:
            value = 0.0
            detail = "empty reference or candidate"
        else:
            lcs = _lcs_length(ref, cand)
            if lcs == 0:
                value = 0.0
                detail = "no overlap"
            else:
                precision = lcs / len(cand)
                recall = lcs / len(ref)
                value = (2 * precision * recall) / (precision + recall)
                detail = (
                    f"lcs={lcs} p={precision:.3f} r={recall:.3f} f1={value:.3f}"
                )
        return _score(
            name="rouge_l",
            sample=sample,
            value=value,
            threshold=threshold,
            detail=detail,
        )

    scorer.name = "rouge_l"  # type: ignore[attr-defined]
    return scorer  # type: ignore[return-value]


def _ngrams(tokens: list[str], n: int) -> list[tuple[str, ...]]:
    if len(tokens) < n:
        return []
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def _modified_precision(
    cand: list[str], ref: list[str], n: int
) -> tuple[int, int]:
    cand_grams = _ngrams(cand, n)
    if not cand_grams:
        return (0, 0)
    ref_counts: dict[tuple[str, ...], int] = {}
    for g in _ngrams(ref, n):
        ref_counts[g] = ref_counts.get(g, 0) + 1
    clipped = 0
    cand_counts: dict[tuple[str, ...], int] = {}
    for g in cand_grams:
        cand_counts[g] = cand_counts.get(g, 0) + 1
    for g, c in cand_counts.items():
        clipped += min(c, ref_counts.get(g, 0))
    return (clipped, len(cand_grams))


def bleu_scorer(*, max_n: int = 4, threshold: float = 0.3) -> Scorer:
    """A small, dependency-free BLEU implementation (corpus = single sample).

    Computes geometric mean of clipped n-gram precisions for n=1..max_n
    multiplied by a brevity penalty, matching Papineni et al. 2002 for the
    single-reference, single-candidate case.
    """

    if not 1 <= max_n <= 4:
        raise ValueError("max_n must be between 1 and 4")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in [0, 1]")

    def scorer(sample: Sample, run: Run) -> object:
        cand = _tokenise(run.output)
        ref = _tokenise(sample.expected or "")
        if not cand or not ref:
            return _score(
                name="bleu",
                sample=sample,
                value=0.0,
                threshold=threshold,
                detail="empty reference or candidate",
            )
        precisions: list[float] = []
        for n in range(1, max_n + 1):
            num, den = _modified_precision(cand, ref, n)
            if den == 0:
                precisions.append(0.0)
            else:
                precisions.append(num / den)
        if any(p == 0.0 for p in precisions):
            value = 0.0
        else:
            import math

            log_avg = sum(math.log(p) for p in precisions) / len(precisions)
            geo_mean = math.exp(log_avg)
            bp = 1.0 if len(cand) > len(ref) else math.exp(1 - len(ref) / len(cand))
            value = bp * geo_mean
        return _score(
            name="bleu",
            sample=sample,
            value=value,
            threshold=threshold,
            detail=(
                f"precisions={[round(p, 3) for p in precisions]} "
                f"score={value:.3f}"
            ),
        )

    scorer.name = "bleu"  # type: ignore[attr-defined]
    return scorer  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# S244 -- tool_call_match scorer.
# --------------------------------------------------------------------------- #


def _args_superset(actual_json: str, expected_json: str) -> bool:
    """Every key/value in ``expected`` must be present in ``actual``."""

    try:
        actual = json.loads(actual_json or "{}")
        expected = json.loads(expected_json or "{}")
    except json.JSONDecodeError:
        return False
    if not isinstance(actual, dict) or not isinstance(expected, dict):
        return actual == expected
    for k, v in expected.items():
        if k not in actual:
            return False
        if actual[k] != v:
            return False
    return True


def tool_call_match(*, ordered: bool = True) -> Scorer:
    """Pass when the run's tool_calls match the sample's expected sequence.

    Matching rules (deterministic, well-defined):

    * ``actual`` must contain a tool invocation for every ``expected``
      tool, with arg superset semantics (see ``_args_superset``).
    * When ``ordered=True`` the names must appear in the same order; extra
      actual calls between expected ones are tolerated.
    * When ``ordered=False`` only the multiset of names matters.
    """

    def scorer(sample: Sample, run: Run) -> object:
        expected: tuple[ToolInvocation, ...] = sample.expected_tool_calls
        actual: tuple[ToolInvocation, ...] = run.tool_calls
        if not expected:
            value = 1.0 if not actual else 0.0
            return _score(
                name="tool_call_match",
                sample=sample,
                value=value,
                threshold=1.0,
                detail=("ok" if value == 1.0 else "unexpected tool calls"),
            )

        if ordered:
            i = 0
            for exp in expected:
                while i < len(actual):
                    if actual[i].name == exp.name and _args_superset(
                        actual[i].args_json, exp.args_json
                    ):
                        i += 1
                        break
                    i += 1
                else:
                    return _score(
                        name="tool_call_match",
                        sample=sample,
                        value=0.0,
                        threshold=1.0,
                        detail=f"missing or out-of-order tool {exp.name!r}",
                    )
            return _score(
                name="tool_call_match",
                sample=sample,
                value=1.0,
                threshold=1.0,
                detail="ordered match",
            )

        remaining: list[ToolInvocation] = list(actual)
        for exp in expected:
            for j, cand in enumerate(remaining):
                if cand.name == exp.name and _args_superset(
                    cand.args_json, exp.args_json
                ):
                    remaining.pop(j)
                    break
            else:
                return _score(
                    name="tool_call_match",
                    sample=sample,
                    value=0.0,
                    threshold=1.0,
                    detail=f"missing tool {exp.name!r}",
                )
        return _score(
            name="tool_call_match",
            sample=sample,
            value=1.0,
            threshold=1.0,
            detail="unordered match",
        )

    scorer.name = "tool_call_match"  # type: ignore[attr-defined]
    return scorer  # type: ignore[return-value]
