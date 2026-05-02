"""Smoke tests for the Postgres PITR drill runbook (S572 / RB-021).

These are intentionally lightweight: we assert that the runbook entry
exists, that the cumulative step budget stays within the published
60-minute RTO, and that the drill driver script's --dry-run mode
produces the canonical 10-line JSON event stream that the evidence
collector indexes.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNBOOKS = ROOT / "loop_implementation" / "engineering" / "RUNBOOKS.md"
DRIVER = ROOT / "scripts" / "dr_postgres_pitr_drill.sh"


def test_rb021_index_row_present() -> None:
    text = RUNBOOKS.read_text()
    assert "| RB-021 | Postgres PITR restore drill |" in text, (
        "RB-021 must appear in the runbook index"
    )


def test_rb021_section_present_with_rto_target() -> None:
    text = RUNBOOKS.read_text()
    assert "## RB-021 — Postgres PITR restore drill" in text
    # The published RTO must be <= 60 minutes per the AC.
    assert "RTO ≤ 60 min" in text


def test_rb021_step_budget_fits_within_rto() -> None:
    """Sum the explicit per-step minute budgets in the steps table and
    assert the total never exceeds 60 min. This locks the runbook
    against drift that would silently breach the SLO.
    """
    text = RUNBOOKS.read_text()
    section = text.split("## RB-021")[1].split("## RB-")[0]
    # Match lines like "| 5 | Drill driver replays …" and pull the
    # right-most "N min" budget cell on that line.
    rows = re.findall(r"^\| \d+\s*\|.*?\| (\d+) min\s*\| (\d+) min\s*\|$",
                      section, re.MULTILINE)
    assert rows, "expected the steps table to contain numbered rows"
    # Every cumulative budget must be ≤ 60.
    cumulatives = [int(c) for _, c in rows]
    assert max(cumulatives) <= 60, (
        f"cumulative drill budget {max(cumulatives)} min exceeds 60 min RTO"
    )
    # The last row's cumulative is the total budget.
    assert cumulatives[-1] <= 60


def test_driver_script_dry_run_emits_ten_ok_steps() -> None:
    """Run the driver in --dry-run mode and assert it emits 10 JSON
    lines, all with ok=true. This is the smoke test we run from CI to
    validate the orchestration logic without touching cloud resources.
    """
    proc = subprocess.run(
        [
            str(DRIVER),
            "--region=us-east-1",
            "--workspace-id=ws_drill_synthetic",
            "--rt=2026-04-30T12:00:00Z",
            "--bucket=s3://test",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [ln for ln in proc.stdout.strip().splitlines() if ln.startswith("{")]
    assert len(lines) == 10, f"expected 10 steps, got {len(lines)}"
    parsed = [json.loads(ln) for ln in lines]
    assert [p["step"] for p in parsed] == list(range(1, 11))
    assert all(p["ok"] is True for p in parsed)
    # The driver must always create a namespace under the drill prefix.
    assert "postgres-drill-" in proc.stderr


def test_driver_script_refuses_missing_required_args() -> None:
    proc = subprocess.run(
        [str(DRIVER), "--dry-run"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "missing --region" in proc.stderr
