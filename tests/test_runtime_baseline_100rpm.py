"""Tests for the S142 runtime 100 turns/minute baseline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "k6_runtime_baseline_100rpm.js"
RESULT = ROOT / "bench" / "results" / "runtime_baseline_100rpm.json"
DOC = ROOT / "docs" / "perf" / "runtime-baseline.md"
WORKFLOW = ROOT / ".github" / "workflows" / "perf-baseline-100rpm.yml"


def _workflow() -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(WORKFLOW.read_text()))


def test_runtime_baseline_k6_script_uses_100rpm_for_5_minutes() -> None:
    script = SCRIPT.read_text()

    assert "const BASELINE_RATE_PER_MINUTE = 100" in script
    assert 'executor: "constant-arrival-rate"' in script
    assert "rate: BASELINE_RATE_PER_MINUTE" in script
    assert 'timeUnit: "1m"' in script
    assert 'duration: "5m"' in script
    assert "/v1/turns" in script


def test_runtime_baseline_report_contains_required_latency_stats() -> None:
    result = json.loads(RESULT.read_text())
    docs = DOC.read_text()

    assert result["name"] == "runtime_baseline_100rpm"
    assert result["stats"]["turns_per_minute"] == 100
    assert {"p50_ms", "p95_ms", "p99_ms", "error_rate"} <= set(result["stats"])
    assert "| p50 latency |" in docs
    assert "| p95 latency |" in docs
    assert "| p99 latency |" in docs
    assert "| error rate |" in docs


def test_runtime_baseline_workflow_runs_nightly_and_asserts_budget() -> None:
    data = _workflow()
    triggers = cast(dict[Any, Any], data.get(True, data.get("on", {})))
    job = cast(dict[str, Any], data["jobs"]["perf-baseline-100rpm"])
    runs = "\n".join(str(step.get("run", "")) for step in cast(list[dict[str, Any]], job["steps"]))

    assert triggers["schedule"][0]["cron"] == "23 6 * * *"
    assert "workflow_dispatch" in triggers
    assert "helm/kind-action@v1.10.0" in WORKFLOW.read_text()
    assert "scripts/Dockerfile.smoke" in runs
    assert "scripts/k6_runtime_baseline_100rpm.js" in runs
    assert "bench/results/runtime_baseline_100rpm.json" in runs
    assert "Assert baseline budget contract" in WORKFLOW.read_text()
    assert "LOOP_ONCALL_WEBHOOK_URL" in runs
