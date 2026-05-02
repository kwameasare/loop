"""Tests for the S840 k6 turn-latency acceptance gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "k6_turn_latency.js"
WORKFLOW = ROOT / ".github" / "workflows" / "turn-latency-k6.yml"
RESULT = ROOT / "bench" / "results" / "turn_latency_text_path_k6.json"


def _workflow() -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(WORKFLOW.read_text()))


def _step_runs(job: dict[str, Any]) -> str:
    steps = cast(list[dict[str, Any]], job["steps"])
    return "\n".join(str(step.get("run", "")) for step in steps)


def test_k6_script_posts_text_turn_and_enforces_p95_budget() -> None:
    script = SCRIPT.read_text()

    assert "const TURN_LATENCY_P95_MS = 2000" in script
    assert "http_req_duration: [`p(95)<${TURN_LATENCY_P95_MS}`]" in script
    assert "http.post(" in script
    assert "`${BASE_URL}/v1/turns`" in script
    assert 'metadata: { smoke: "turn-latency-k6", path: "text" }' in script
    assert '"turn response has text"' in script


def test_turn_latency_workflow_runs_nightly_k6_and_pages_on_failure() -> None:
    data = _workflow()
    job = cast(dict[str, Any], data["jobs"]["turn-latency-k6"])
    steps = cast(list[dict[str, Any]], job["steps"])
    triggers = cast(dict[str, Any], data.get(True, data.get("on", {})))
    runs = _step_runs(job)

    assert triggers["schedule"][0]["cron"] == "43 5 * * *"
    assert "workflow_dispatch" in triggers
    assert job["timeout-minutes"] == 14
    assert job["env"]["LOOP_TURN_LATENCY_BASE_URL"] == "http://127.0.0.1:18081"
    assert any(step.get("uses") == "grafana/setup-k6-action@v1" for step in steps)
    assert any(step.get("uses") == "helm/kind-action@v1.10.0" for step in steps)
    assert "helm upgrade --install" in runs
    assert 'kubectl -n "$LOOP_NAMESPACE" port-forward svc/loop-loop-runtime 18081:8081' in runs
    assert (
        "k6 run --summary-export /tmp/turn-latency-k6-summary.json scripts/k6_turn_latency.js"
    ) in runs

    notify = next(step for step in steps if step.get("name") == "Page on-call")
    assert notify["if"] == "failure()"
    assert notify["env"]["LOOP_ONCALL_WEBHOOK_URL"] == "${{ secrets.LOOP_ONCALL_WEBHOOK_URL }}"


def test_turn_latency_contract_result_matches_budget() -> None:
    result = json.loads(RESULT.read_text())

    assert result["name"] == "turn_latency_text_path_k6"
    assert result["tool"] == "k6"
    assert result["source"] == ".github/workflows/turn-latency-k6.yml"
    assert result["stats"]["p95_ms"] < result["budgets"]["p95_ms"]
    assert result["stats"]["http_req_failed_rate"] < result["budgets"]["http_req_failed_rate"]
    assert result["stats"]["checks_rate"] > result["budgets"]["checks_rate"]
