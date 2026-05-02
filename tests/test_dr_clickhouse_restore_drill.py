"""Smoke tests for the ClickHouse snapshot restore drill (S573 / RB-022)."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNBOOKS = ROOT / "loop_implementation" / "engineering" / "RUNBOOKS.md"
DRIVER = ROOT / "scripts" / "dr_clickhouse_restore_drill.sh"


def test_rb022_index_row_present() -> None:
    text = RUNBOOKS.read_text()
    assert "| RB-022 | ClickHouse snapshot restore drill |" in text


def test_rb022_section_present_with_rto_target() -> None:
    text = RUNBOOKS.read_text()
    assert "## RB-022 — ClickHouse snapshot restore drill" in text
    assert "RTO ≤ 90 min" in text


def test_rb022_step_budget_fits_within_rto() -> None:
    text = RUNBOOKS.read_text()
    section = text.split("## RB-022")[1].split("## RB-")[0].split("## How to add")[0]
    rows = re.findall(r"^\| \d+\s*\|.*?\| (\d+) min\s*\| (\d+) min\s*\|$",
                      section, re.MULTILINE)
    assert rows, "expected the steps table to contain numbered rows"
    cumulatives = [int(c) for _, c in rows]
    assert max(cumulatives) <= 90, (
        f"cumulative drill budget {max(cumulatives)} min exceeds 90 min RTO"
    )
    assert cumulatives[-1] <= 90


def test_driver_dry_run_emits_ten_ok_steps() -> None:
    proc = subprocess.run(
        [
            str(DRIVER),
            "--region=us-east-1",
            "--snapshot=2026-05-01-daily",
            "--bucket=s3://test",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [ln for ln in proc.stdout.strip().splitlines() if ln.startswith("{")]
    assert len(lines) == 10
    parsed = [json.loads(ln) for ln in lines]
    assert [p["step"] for p in parsed] == list(range(1, 11))
    assert all(p["ok"] is True for p in parsed)
    assert "clickhouse-drill-" in proc.stderr


def test_driver_refuses_missing_required_args() -> None:
    proc = subprocess.run(
        [str(DRIVER), "--dry-run"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "missing --region" in proc.stderr
