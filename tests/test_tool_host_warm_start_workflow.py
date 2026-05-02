"""Workflow checks for the S843 tool-host warm-start gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "tool-host-warm-start.yml"
RESULT = ROOT / "bench" / "results" / "tool_host_warm_start.json"
DOC = ROOT / "docs" / "perf" / "tool_host_warm_start.md"


def test_tool_host_warm_start_workflow_runs_nightly_and_pages() -> None:
    data = cast(dict[Any, Any], yaml.safe_load(WORKFLOW.read_text()))
    triggers = cast(dict[Any, Any], data.get(True, data.get("on", {})))
    job = cast(dict[str, Any], data["jobs"]["tool-host-warm-start"])
    steps = cast(list[dict[str, Any]], job["steps"])
    runs = "\n".join(str(step.get("run", "")) for step in steps)

    assert triggers["schedule"][0]["cron"] == "58 5 * * *"
    assert "workflow_dispatch" in triggers
    assert "scripts/tool_host_warm_start.py" in runs
    assert "--target-p95-ms 300" in runs
    assert any(step.get("name") == "Upload warm-start report" for step in steps)
    assert any(
        step.get("name") == "Page on-call" and step.get("if") == "failure()" for step in steps
    )


def test_tool_host_warm_start_report_and_docs_are_published() -> None:
    payload = json.loads(RESULT.read_text())
    docs = DOC.read_text()

    assert payload["name"] == "tool_host_warm_start"
    assert payload["p95_ms"] < 300
    assert payload["passed"] is True
    assert "300 ms" in docs
    assert "scripts/tool_host_warm_start.py" in docs
