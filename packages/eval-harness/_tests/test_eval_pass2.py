"""Tests for S242, S244, S246, S247, S248, S249, S250, S251."""

from __future__ import annotations

import asyncio
import io
import json
import sys
from pathlib import Path

import pytest
from loop_eval import (
    CassetteMiss,
    CassetteRecorder,
    CassetteReplayer,
    EvalReport,
    ParallelEvalRunner,
    Run,
    Sample,
    Score,
    ToolInvocation,
    bleu_scorer,
    detect_regression,
    dump_report,
    exact_match,
    load_report,
    load_suite,
    load_suites,
    parse_entry,
    request_key,
    rouge_l,
    serialise_entry,
    tool_call_match,
)
from loop_eval.cli import main as cli_main

# --------------------------------------------------------------------------- #
# S242 -- ROUGE-L + BLEU
# --------------------------------------------------------------------------- #


def _sample(expected: str | None = None, sid: str = "s1") -> Sample:
    return Sample(id=sid, input="q", expected=expected)


def _run(output: str, sid: str = "s1") -> Run:
    return Run(sample_id=sid, output=output, latency_ms=1.0, cost_usd=0.0)


def test_rouge_l_perfect_match() -> None:
    sc = rouge_l()
    score = sc(_sample("the cat sat on the mat"), _run("the cat sat on the mat"))
    assert isinstance(score, Score)
    assert score.value == pytest.approx(1.0)
    assert score.passed


def test_rouge_l_partial_overlap() -> None:
    sc = rouge_l(threshold=0.4)
    score = sc(_sample("the cat sat"), _run("the dog sat"))
    assert isinstance(score, Score)
    # LCS = "the sat" => p=2/3, r=2/3, f1=2/3 ≈ 0.667
    assert 0.6 < score.value < 0.7
    assert score.passed


def test_rouge_l_zero_when_empty() -> None:
    sc = rouge_l()
    score = sc(_sample(None), _run("anything"))
    assert isinstance(score, Score)
    assert score.value == 0.0
    assert not score.passed


def test_bleu_perfect_match() -> None:
    sc = bleu_scorer(threshold=0.9)
    score = sc(
        _sample("the quick brown fox jumps"),
        _run("the quick brown fox jumps"),
    )
    assert isinstance(score, Score)
    assert score.value == pytest.approx(1.0)


def test_bleu_partial_match_penalised() -> None:
    sc = bleu_scorer(max_n=2, threshold=0.3)
    score = sc(
        _sample("the cat sat on the mat today"),
        _run("the cat sat on the rug today"),
    )
    assert isinstance(score, Score)
    assert 0.3 < score.value < 1.0


def test_bleu_validates_max_n() -> None:
    with pytest.raises(ValueError):
        bleu_scorer(max_n=0)
    with pytest.raises(ValueError):
        bleu_scorer(max_n=5)


# --------------------------------------------------------------------------- #
# S244 -- tool_call_match
# --------------------------------------------------------------------------- #


def test_tool_call_match_ordered_pass() -> None:
    sc = tool_call_match()
    sample = Sample(
        id="s1",
        input="q",
        expected_tool_calls=(
            ToolInvocation(name="search", args_json='{"q":"x"}'),
            ToolInvocation(name="answer"),
        ),
    )
    run = Run(
        sample_id="s1",
        output="ok",
        latency_ms=1.0,
        cost_usd=0.0,
        tool_calls=(
            ToolInvocation(name="search", args_json='{"q":"x","limit":5}'),
            ToolInvocation(name="answer"),
        ),
    )
    score = sc(sample, run)
    assert isinstance(score, Score)
    assert score.passed


def test_tool_call_match_ordered_fails_on_missing_tool() -> None:
    sc = tool_call_match()
    sample = Sample(
        id="s1",
        input="q",
        expected_tool_calls=(ToolInvocation(name="search"),),
    )
    run = Run(
        sample_id="s1",
        output="ok",
        latency_ms=1.0,
        cost_usd=0.0,
        tool_calls=(ToolInvocation(name="answer"),),
    )
    score = sc(sample, run)
    assert isinstance(score, Score)
    assert not score.passed
    assert "search" in score.detail


def test_tool_call_match_ordered_fails_when_args_diverge() -> None:
    sc = tool_call_match()
    sample = Sample(
        id="s1",
        input="q",
        expected_tool_calls=(
            ToolInvocation(name="search", args_json='{"q":"x"}'),
        ),
    )
    run = Run(
        sample_id="s1",
        output="ok",
        latency_ms=1.0,
        cost_usd=0.0,
        tool_calls=(
            ToolInvocation(name="search", args_json='{"q":"y"}'),
        ),
    )
    score = sc(sample, run)
    assert isinstance(score, Score)
    assert not score.passed


def test_tool_call_match_unordered() -> None:
    sc = tool_call_match(ordered=False)
    sample = Sample(
        id="s1",
        input="q",
        expected_tool_calls=(
            ToolInvocation(name="a"),
            ToolInvocation(name="b"),
        ),
    )
    run = Run(
        sample_id="s1",
        output="ok",
        latency_ms=1.0,
        cost_usd=0.0,
        tool_calls=(
            ToolInvocation(name="b"),
            ToolInvocation(name="a"),
        ),
    )
    score = sc(sample, run)
    assert isinstance(score, Score)
    assert score.passed


def test_tool_call_match_no_expected_passes_only_when_run_empty() -> None:
    sc = tool_call_match()
    sample = Sample(id="s1", input="q")
    score_a = sc(sample, _run("ok"))
    assert isinstance(score_a, Score) and score_a.passed
    score_b = sc(
        sample,
        Run(
            sample_id="s1",
            output="ok",
            latency_ms=1.0,
            cost_usd=0.0,
            tool_calls=(ToolInvocation(name="x"),),
        ),
    )
    assert isinstance(score_b, Score) and not score_b.passed


# --------------------------------------------------------------------------- #
# S246 / S247 -- cassette format + recorder + replayer
# --------------------------------------------------------------------------- #


def test_request_key_is_stable_and_order_independent() -> None:
    a = request_key({"a": 1, "b": 2})
    b = request_key({"b": 2, "a": 1})
    assert a == b


def test_recorder_writes_jsonl_and_replayer_round_trips() -> None:
    buf = io.StringIO()
    rec = CassetteRecorder(buf)
    req = {"prompt": "hi", "model": "gpt-4"}
    rec.record(
        request=req,
        response="hello",
        usage={"in_tok": 10, "out_tok": 2},
        recorded_at_ms=42,
    )
    rec.record(
        request={"prompt": "bye", "model": "gpt-4"},
        response="goodbye",
        usage={},
        recorded_at_ms=43,
    )
    assert rec.count == 2
    lines = buf.getvalue().strip().splitlines()
    assert len(lines) == 2
    entries = [parse_entry(line) for line in lines]
    rep = CassetteReplayer(entries)
    assert len(rep) == 2
    assert req in rep
    assert rep.lookup(req).response == "hello"


def test_replayer_miss_raises() -> None:
    rep = CassetteReplayer([])
    with pytest.raises(CassetteMiss):
        rep.lookup({"x": 1})


def test_recorder_to_path_round_trip(tmp_path: Path) -> None:
    p = tmp_path / "cassette.jsonl"
    rec = CassetteRecorder.to_path(p)
    rec.record(
        request={"q": "ping"},
        response="pong",
        usage={"in_tok": 1.0},
        recorded_at_ms=1,
    )
    rec.close()
    rep = CassetteReplayer.from_path(p)
    assert rep.lookup({"q": "ping"}).response == "pong"


def test_serialise_entry_round_trip() -> None:
    buf = io.StringIO()
    rec = CassetteRecorder(buf)
    entry = rec.record(
        request={"a": 1}, response="b", usage={}, recorded_at_ms=2
    )
    line = serialise_entry(entry)
    assert parse_entry(line) == entry


# --------------------------------------------------------------------------- #
# S248 -- YAML suite loader
# --------------------------------------------------------------------------- #


def _write(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_load_suite_basic(tmp_path: Path) -> None:
    p = _write(
        tmp_path / "smoke.yml",
        """
suite: smoke
samples:
  - id: a
    input: hi
    expected: hello
  - id: b
    input: bye
    metadata:
      lang: en
""",
    )
    suite = load_suite(p)
    assert suite.name == "smoke"
    assert len(suite.samples) == 2
    assert suite.samples[1].metadata == {"lang": "en"}


def test_load_suite_with_tool_calls(tmp_path: Path) -> None:
    p = _write(
        tmp_path / "tc.yml",
        """
samples:
  - id: t1
    input: q
    expected_tool_calls:
      - name: search
        args:
          q: "x"
      - name: answer
""",
    )
    suite = load_suite(p)
    tcs = suite.samples[0].expected_tool_calls
    assert [t.name for t in tcs] == ["search", "answer"]
    assert json.loads(tcs[0].args_json) == {"q": "x"}


def test_load_suite_missing_samples_raises(tmp_path: Path) -> None:
    p = _write(tmp_path / "bad.yml", "suite: x\n")
    from loop_eval.suite_loader import SuiteLoadError

    with pytest.raises(SuiteLoadError):
        load_suite(p)


def test_load_suites_directory(tmp_path: Path) -> None:
    _write(tmp_path / "a.yml", "samples:\n  - id: a\n    input: hi\n")
    _write(tmp_path / "b.yaml", "samples:\n  - id: b\n    input: bye\n")
    suites = load_suites(tmp_path)
    assert [s.name for s in suites] == ["a", "b"]


# --------------------------------------------------------------------------- #
# S249 -- parallel runner
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_parallel_runner_results_are_deterministic_by_sample_id() -> None:
    samples = [
        Sample(id=f"s{i}", input=str(i), expected=str(i)) for i in range(5)
    ]

    async def agent(sample: Sample) -> tuple[str, float]:
        # Vary delay so completion order != input order.
        await asyncio.sleep(0.001 * (5 - int(sample.id[1:])))
        return (sample.expected or "", 0.0)

    runner = ParallelEvalRunner([exact_match], concurrency=4)
    report = await runner.run(dataset=samples, agent=agent)
    assert [r.sample_id for r in report.runs] == [f"s{i}" for i in range(5)]
    assert report.pass_rate == 1.0


@pytest.mark.asyncio
async def test_parallel_runner_per_case_timeout_marks_run() -> None:
    samples = [Sample(id="slow", input="q", expected="x")]

    async def agent(_: Sample) -> tuple[str, float]:
        await asyncio.sleep(0.5)
        return ("x", 0.0)

    runner = ParallelEvalRunner(
        [exact_match], concurrency=1, per_case_timeout_s=0.05
    )
    report = await runner.run(dataset=samples, agent=agent)
    assert report.runs[0].metadata.get("timeout") == "true"
    assert not any(s.passed for s in report.scores)


@pytest.mark.asyncio
async def test_parallel_runner_captures_agent_exceptions() -> None:
    samples = [Sample(id="boom", input="q", expected="x")]

    async def agent(_: Sample) -> tuple[str, float]:
        raise RuntimeError("kaboom")

    runner = ParallelEvalRunner([exact_match], concurrency=1)
    report = await runner.run(dataset=samples, agent=agent)
    assert report.runs[0].metadata.get("error") == "RuntimeError"


def test_parallel_runner_validates_args() -> None:
    with pytest.raises(ValueError):
        ParallelEvalRunner([], concurrency=1)
    with pytest.raises(ValueError):
        ParallelEvalRunner([exact_match], concurrency=0)
    with pytest.raises(ValueError):
        ParallelEvalRunner([exact_match], per_case_timeout_s=0)


# --------------------------------------------------------------------------- #
# S250 -- regression detector
# --------------------------------------------------------------------------- #


def _report(scores: list[tuple[str, str, float, bool]]) -> EvalReport:
    runs = tuple(
        Run(sample_id=sid, output="x", latency_ms=1.0, cost_usd=0.0)
        for _, sid, _, _ in scores
    )
    score_objs = tuple(
        Score(scorer=name, sample_id=sid, value=val, passed=passed)
        for name, sid, val, passed in scores
    )
    return EvalReport(
        samples=len(runs),
        runs=runs,
        scores=score_objs,
        pass_rate=sum(1 for s in score_objs if s.passed) / max(len(score_objs), 1),
        mean_latency_ms=1.0,
        total_cost_usd=0.0,
    )


def test_regression_detected_when_mean_drops_above_threshold() -> None:
    base = _report(
        [("exact_match", "a", 1.0, True), ("exact_match", "b", 1.0, True)]
    )
    cur = _report(
        [("exact_match", "a", 1.0, True), ("exact_match", "b", 0.0, False)]
    )
    rep = detect_regression(baseline=base, current=cur, threshold=0.05)
    assert rep.regressed
    assert rep.scorer_deltas[0].relative_delta < -0.05
    assert rep.flips and rep.flips[0].sample_id == "b"


def test_no_regression_when_means_stable() -> None:
    r = _report(
        [("exact_match", "a", 1.0, True), ("exact_match", "b", 1.0, True)]
    )
    assert not detect_regression(baseline=r, current=r).regressed


def test_dump_load_report_round_trip(tmp_path: Path) -> None:
    r = _report([("exact_match", "a", 1.0, True)])
    p = tmp_path / "report.json"
    dump_report(r, p)
    assert load_report(p) == r


def test_regression_threshold_bounds() -> None:
    r = _report([("exact_match", "a", 1.0, True)])
    with pytest.raises(ValueError):
        detect_regression(baseline=r, current=r, threshold=1.0)


# --------------------------------------------------------------------------- #
# S251 -- CLI
# --------------------------------------------------------------------------- #


# A module-level factory the CLI can resolve.
async def _factory_pass_through() -> object:
    async def _agent(sample: Sample) -> tuple[str, float]:
        return (sample.expected or "", 0.0)

    return _agent


async def _factory_always_wrong() -> object:
    async def _agent(_: Sample) -> tuple[str, float]:
        return ("nope", 0.0)

    return _agent


# Expose factories under loop_eval._tests path for resolver.
sys.modules[__name__]._factory_pass_through = _factory_pass_through  # type: ignore[attr-defined]
sys.modules[__name__]._factory_always_wrong = _factory_always_wrong  # type: ignore[attr-defined]


def test_cli_tap_exit_zero_on_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    suite = _write(
        tmp_path / "ok.yml",
        "samples:\n  - id: a\n    input: hi\n    expected: hi\n",
    )
    rc = cli_main(
        [
            str(suite),
            "--agent-factory",
            f"{__name__}:_factory_pass_through",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "TAP version 13" in out
    assert "ok 1 -" in out


def test_cli_tap_exit_one_on_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    suite = _write(
        tmp_path / "bad.yml",
        "samples:\n  - id: a\n    input: hi\n    expected: hi\n",
    )
    rc = cli_main(
        [
            str(suite),
            "--agent-factory",
            f"{__name__}:_factory_always_wrong",
        ]
    )
    assert rc == 1
    assert "not ok" in capsys.readouterr().out


def test_cli_json_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    suite = _write(
        tmp_path / "ok.yml",
        "samples:\n  - id: a\n    input: hi\n    expected: hi\n",
    )
    rc = cli_main(
        [
            str(suite),
            "--agent-factory",
            f"{__name__}:_factory_pass_through",
            "--json",
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 0
    assert payload["suites"][0]["report"]["samples"] == 1
