"""Unit checks for tools/stamp_runbook_drill_date.py."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import stamp_runbook_drill_date as stamp  # type: ignore[import-not-found]


def test_stamp_updates_last_drilled_cell(tmp_path: Path) -> None:
    runbooks = tmp_path / "RUNBOOKS.md"
    runbooks.write_text(
        "\n".join(
            [
                "| ID | Title | Owner | Last drilled | SEV target |",
                "|----|-------|-------|--------------|-----------|",
                "| RB-021 | Postgres PITR restore drill | Eng #2 | TBD M2 | SEV1 |",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    stamp.stamp_runbook_date(runbooks, "RB-021", "2026-05-04")

    text = runbooks.read_text(encoding="utf-8")
    assert "| RB-021 | Postgres PITR restore drill | Eng #2 | 2026-05-04 (ci) | SEV1 |" in text
