"""Tests for the S845 cp-api 5000 RPS gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "k6_cp_api_5000.js"
WORKFLOW = ROOT / ".github" / "workflows" / "cp-api-5000-rps.yml"
RESULT = ROOT / "bench" / "results" / "cp_api_5000_rps.json"
DOC = ROOT / "docs" / "perf" / "cp_api_5000_rps.md"


def _workflow() -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(WORKFLOW.read_text()))


def _step_runs(job: dict[str, Any]) -> str:
    steps = cast(list[dict[str, Any]], job["steps"])
    return "\n".join(str(step.get("run", "")) for step in steps)


def test_k6_cp_api_script_enforces_5000_rps_budget() -> None:
    script = SCRIPT.read_text()

    assert "const CP_API_TARGET_RPS = 5000" in script
    assert "const CP_API_P95_MS = 100" in script
    assert 'executor: "constant-arrival-rate"' in script
    assert "rate: CP_API_TARGET_RPS" in script
    assert "/healthz" in script
    assert 'http_req_failed: ["rate<0.001"]' in script


def test_cp_api_5000_rps_workflow_runs_k6_and_pages() -> None:
    data = _workflow()
    job = cast(dict[str, Any], data["jobs"]["cp-api-5000-rps"])
    triggers = cast(dict[str, Any], data.get(True, data.get("on", {})))
    runs = _step_runs(job)

    assert triggers["schedule"][0]["cron"] == "13 6 * * *"
    assert "workflow_dispatch" in triggers
    assert "svc/loop-loop-control-plane 18080:8080" in runs
    assert "k6 run --summary-export /tmp/cp-api-5000-rps-summary.json" in runs
    assert "scripts/k6_cp_api_5000.js" in runs
    assert "LOOP_ONCALL_WEBHOOK_URL" in runs


def test_cp_api_5000_rps_contract_result_and_docs_match_budget() -> None:
    result = json.loads(RESULT.read_text())
    docs = DOC.read_text()

    assert result["name"] == "cp_api_5000_rps"
    assert result["stats"]["rps"] == 5000
    assert result["stats"]["p95_ms"] < result["budgets"]["p95_ms"]
    assert result["stats"]["http_req_failed_rate"] < result["budgets"]["http_req_failed_rate"]
    assert "5000 requests per second" in docs
    assert "100 ms" in docs
