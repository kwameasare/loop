"""Workflow checks for the S841 gateway cache hit-ratio gate."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "gateway-cache-hit-ratio.yml"
RESULT = ROOT / "bench" / "results" / "gateway_cache_hit_ratio.json"
DOC = ROOT / "docs" / "perf" / "gateway_cache_hit_ratio.md"


def _workflow() -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(WORKFLOW.read_text()))


def test_gateway_cache_hit_ratio_workflow_runs_nightly_and_pages() -> None:
    data = _workflow()
    triggers = cast(dict[Any, Any], data.get(True, data.get("on", {})))
    job = cast(dict[str, Any], data["jobs"]["gateway-cache-hit-ratio"])
    steps = cast(list[dict[str, Any]], job["steps"])
    runs = "\n".join(str(step.get("run", "")) for step in steps)

    assert triggers["schedule"][0]["cron"] == "52 5 * * *"
    assert "workflow_dispatch" in triggers
    assert "scripts/gateway_cache_hit_ratio.py" in runs
    assert "--min-hit-ratio 0.30" in runs
    assert any(step.get("name") == "Upload cache hit-ratio report" for step in steps)
    assert any(
        step.get("name") == "Page on-call" and step.get("if") == "failure()" for step in steps
    )


def test_gateway_cache_hit_ratio_report_and_docs_are_published() -> None:
    payload = yaml.safe_load(RESULT.read_text())
    docs = DOC.read_text()

    assert payload["name"] == "gateway_cache_hit_ratio_fixed_eval"
    assert payload["hit_ratio"] >= 0.30
    assert payload["passed"] is True
    assert "30%" in docs
    assert "scripts/gateway_cache_hit_ratio.py" in docs
