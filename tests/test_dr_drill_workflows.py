"""Workflow checks for weekly DR drill automation and runbook stamping."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
PG_WORKFLOW = ROOT / ".github" / "workflows" / "dr-drill-postgres.yml"
CH_WORKFLOW = ROOT / ".github" / "workflows" / "dr-drill-clickhouse.yml"


def _load(path: Path) -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(path.read_text()))


def test_postgres_dr_workflow_runs_weekly_and_stamps_rb021() -> None:
    data = _load(PG_WORKFLOW)
    triggers = cast(dict[Any, Any], data.get(True, data.get("on", {})))
    job = cast(dict[str, Any], data["jobs"]["dr-drill-postgres"])
    runs = "\n".join(str(step.get("run", "")) for step in cast(list[dict[str, Any]], job["steps"]))

    assert {"cron": "5 4 * * 1"} in triggers["schedule"]
    assert "workflow_dispatch" in triggers
    assert "scripts/dr_postgres_pitr_drill.sh" in runs
    assert "--dry-run" in runs
    assert "stamp_runbook_drill_date.py" in runs
    assert "--runbook-id RB-021" in runs


def test_clickhouse_dr_workflow_runs_weekly_and_stamps_rb022() -> None:
    data = _load(CH_WORKFLOW)
    triggers = cast(dict[Any, Any], data.get(True, data.get("on", {})))
    job = cast(dict[str, Any], data["jobs"]["dr-drill-clickhouse"])
    runs = "\n".join(str(step.get("run", "")) for step in cast(list[dict[str, Any]], job["steps"]))

    assert {"cron": "35 4 * * 1"} in triggers["schedule"]
    assert "workflow_dispatch" in triggers
    assert "scripts/dr_clickhouse_restore_drill.sh" in runs
    assert "--dry-run" in runs
    assert "stamp_runbook_drill_date.py" in runs
    assert "--runbook-id RB-022" in runs
