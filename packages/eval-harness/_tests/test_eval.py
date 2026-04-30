from __future__ import annotations

import pytest
from loop_eval import (
    EvalRunner,
    Sample,
    Score,
    cost_scorer,
    exact_match,
    json_schema_scorer,
    latency_scorer,
    llm_judge,
    regex_match,
)
from loop_eval.models import Run


def _run(output: str = "hi", latency_ms: float = 1.0, cost: float = 0.0) -> Run:
    return Run(sample_id="s1", output=output, latency_ms=latency_ms, cost_usd=cost)


def _sample(expected: str | None = "hi") -> Sample:
    return Sample(id="s1", input="say hi", expected=expected)


def test_exact_match() -> None:
    s = exact_match(_sample(), _run("hi"))
    assert isinstance(s, Score)
    assert s.passed and s.value == 1.0
    s2 = exact_match(_sample(), _run("bye"))
    assert isinstance(s2, Score)
    assert not s2.passed


def test_regex_match() -> None:
    scorer = regex_match(r"^h\w+$")
    s = scorer(_sample(), _run("hello"))
    assert isinstance(s, Score) and s.passed
    s2 = scorer(_sample(), _run("nope"))
    assert isinstance(s2, Score) and not s2.passed


def test_json_schema_scorer() -> None:
    scorer = json_schema_scorer(("name", "age"))
    ok = scorer(_sample(), _run('{"name":"a","age":1}'))
    assert isinstance(ok, Score) and ok.passed
    missing = scorer(_sample(), _run('{"name":"a"}'))
    assert isinstance(missing, Score) and not missing.passed
    bad = scorer(_sample(), _run("not json"))
    assert isinstance(bad, Score) and not bad.passed


def test_llm_judge_calls_injected_function() -> None:
    def judge(_input, _expected, output):
        return (1.0 if "yes" in output else 0.0, "saw 'yes'")

    scorer = llm_judge(judge, threshold=0.5)
    s = scorer(_sample(), _run("yes really"))
    assert isinstance(s, Score) and s.passed
    s2 = scorer(_sample(), _run("nope"))
    assert isinstance(s2, Score) and not s2.passed


def test_latency_and_cost_scorers() -> None:
    lat = latency_scorer(max_ms=100)
    s = lat(_sample(), _run(latency_ms=50))
    assert isinstance(s, Score) and s.passed and s.value == pytest.approx(1.0)
    s2 = lat(_sample(), _run(latency_ms=200))
    assert isinstance(s2, Score) and not s2.passed and s2.value < 1.0
    c = cost_scorer(max_usd=0.01)
    s3 = c(_sample(), _run(cost=0.005))
    assert isinstance(s3, Score) and s3.passed
    s4 = c(_sample(), _run(cost=0.05))
    assert isinstance(s4, Score) and not s4.passed


def test_latency_scorer_rejects_nonpositive_max() -> None:
    with pytest.raises(ValueError, match="max_ms"):
        latency_scorer(max_ms=0)


@pytest.mark.asyncio
async def test_eval_runner_aggregates_report() -> None:
    async def agent(sample: Sample) -> tuple[str, float]:
        return (sample.expected or "", 0.001)

    dataset = [
        Sample(id="a", input="x", expected="hi"),
        Sample(id="b", input="y", expected="bye"),
    ]
    runner = EvalRunner([exact_match])
    report = await runner.run(dataset=dataset, agent=agent)
    assert report.samples == 2
    assert report.pass_rate == 1.0
    assert report.total_cost_usd == pytest.approx(0.002)
    assert all(s.passed for s in report.scores)


def test_eval_runner_requires_at_least_one_scorer() -> None:
    with pytest.raises(ValueError, match="scorer"):
        EvalRunner([])
