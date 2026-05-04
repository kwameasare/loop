"""Workflow checks for the gateway COST_TABLE freshness monitor."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "cost-table-staleness.yml"


def _workflow() -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(WORKFLOW.read_text()))


def test_cost_table_staleness_workflow_runs_weekly_and_manually() -> None:
    data = _workflow()
    triggers = cast(dict[Any, Any], data.get(True, data.get("on", {})))
    job = cast(dict[str, Any], data["jobs"]["cost-table-staleness"])
    steps = cast(list[dict[str, Any]], job["steps"])
    runs = "\n".join(str(step.get("run", "")) for step in steps)

    assert triggers["schedule"][0]["cron"] == "17 6 * * 1"
    assert "workflow_dispatch" in triggers
    assert "cost_health_check(max_age_days=60)" in runs
    assert "gh issue create" in runs
    assert any(step.get("name") == "Open refresh issue" for step in steps)


def test_cost_table_staleness_workflow_can_create_issues() -> None:
    data = _workflow()
    permissions = cast(dict[str, str], data["permissions"])
    assert permissions["contents"] == "read"
    assert permissions["issues"] == "write"
