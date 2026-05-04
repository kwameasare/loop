"""Workflow and script checks for the S846 p95 regression budget."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from scripts.perf_regression_budget import compare_budget, main

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "perf-regression-budget.yml"
BASELINE = ROOT / "bench" / "results" / "perf_7d_baseline.json"
RESULT = ROOT / "bench" / "results" / "perf_regression_budget.json"
DOC = ROOT / "docs" / "perf" / "perf_regression_budget.md"


def test_perf_regression_budget_writes_passing_report(tmp_path: Path) -> None:
    output = tmp_path / "perf_regression_budget.json"

    assert main(["--baseline", str(BASELINE), "--output", str(output)]) == 0

    payload = json.loads(output.read_text())
    assert payload["name"] == "perf_regression_budget"
    assert payload["window_days"] == 7
    assert payload["max_p95_regression_percent"] == 5.0
    assert payload["passed"] is True
    assert payload["breaches"] == []
    assert {item["name"] for item in payload["metrics"]} == set(
        json.loads(BASELINE.read_text())["metrics"]
    )


def test_perf_regression_budget_fails_on_five_percent_p95_regression(tmp_path: Path) -> None:
    current = tmp_path / "current.json"
    current.write_text(json.dumps({"stats": {"p95_ms": 105.0}}))
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps(
            {
                "window_days": 7,
                "max_p95_regression_percent": 5.0,
                "metrics": {"turn_latency": {"source": str(current), "p95_ms": 100.0}},
            }
        )
    )
    output = tmp_path / "out.json"

    assert main(["--baseline", str(baseline), "--output", str(output)]) == 2

    payload = json.loads(output.read_text())
    assert payload["passed"] is False
    assert payload["breaches"][0]["name"] == "turn_latency"
    assert payload["breaches"][0]["regression_percent"] == 5.0


def test_perf_regression_budget_extracts_top_level_and_nested_p95(tmp_path: Path) -> None:
    top = tmp_path / "top.json"
    nested = tmp_path / "nested.json"
    top.write_text(json.dumps({"p95_ms": 9.0}))
    nested.write_text(json.dumps({"stats": {"p95_ms": 10.0}}))
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps(
            {
                "window_days": 7,
                "max_p95_regression_percent": 5.0,
                "metrics": {
                    "nested": {"source": str(nested), "p95_ms": 10.0},
                    "top": {"source": str(top), "p95_ms": 10.0},
                },
            }
        )
    )

    _, comparisons = compare_budget(baseline)

    assert [item["name"] for item in comparisons] == ["nested", "top"]
    assert [item["current_p95_ms"] for item in comparisons] == [10.0, 9.0]


def test_perf_regression_budget_rejects_missing_p95(tmp_path: Path) -> None:
    current = tmp_path / "current.json"
    current.write_text(json.dumps({"stats": {"p50_ms": 1.0}}))
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps(
            {
                "window_days": 7,
                "max_p95_regression_percent": 5.0,
                "metrics": {"bad": {"source": str(current), "p95_ms": 1.0}},
            }
        )
    )

    with pytest.raises(ValueError, match="does not expose p95_ms"):
        compare_budget(baseline)


def test_perf_regression_budget_workflow_runs_on_pr_and_pages() -> None:
    data = cast(dict[Any, Any], yaml.safe_load(WORKFLOW.read_text()))
    triggers = cast(dict[Any, Any], data.get(True, data.get("on", {})))
    job = cast(dict[str, Any], data["jobs"]["perf-regression-budget"])
    steps = cast(list[dict[str, Any]], job["steps"])
    runs = "\n".join(str(step.get("run", "")) for step in steps)

    assert triggers["schedule"][0]["cron"] == "29 6 * * *"
    assert "pull_request" in triggers
    assert "scripts/perf_regression_budget.py" in runs
    assert "bench/results/perf_7d_baseline.json" in runs
    assert "continue-on-error" not in yaml.safe_dump(job)
    assert not any(step.get("name") == "Fail breached p95 regression budget" for step in steps)
    assert any(step.get("name") == "Upload perf regression report" for step in steps)
    assert any(
        step.get("name") == "Page on-call" and step.get("if") == "failure()" for step in steps
    )


def test_perf_regression_budget_report_and_docs_are_published() -> None:
    payload = json.loads(RESULT.read_text())
    docs = DOC.read_text()

    assert payload["name"] == "perf_regression_budget"
    assert payload["window_days"] == 7
    assert payload["max_p95_regression_percent"] == 5.0
    assert payload["passed"] is True
    assert "5%+ p95 regression" in docs
    assert "scripts/perf_regression_budget.py" in docs
