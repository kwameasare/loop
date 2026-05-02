"""Validate the design-partner → paid-customer launch ledger (S672).

Acceptance criterion: every partner is **converted or churned with reason**,
documented in `OPS/launch.md` (we use
`loop_implementation/operations/launch.md` to keep the corpus together).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LAUNCH_DOC = (
    REPO_ROOT / "loop_implementation" / "operations" / "launch.md"
)

VALID_OUTCOMES = ("CONVERTED", "CHURNED")


def _table_rows() -> list[list[str]]:
    body = LAUNCH_DOC.read_text(encoding="utf-8")
    rows: list[list[str]] = []
    for line in body.splitlines():
        if not line.startswith("|"):
            continue
        # Skip the header row and the separator row.
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or cells[0] in {"#", "--"} or cells[0].startswith("--"):
            continue
        if not re.fullmatch(r"\d+", cells[0]):
            continue
        rows.append(cells)
    return rows


def test_launch_doc_exists() -> None:
    assert LAUNCH_DOC.exists(), f"missing {LAUNCH_DOC}"


def test_exactly_ten_partner_rows() -> None:
    rows = _table_rows()
    assert len(rows) == 10, f"expected 10 partner rows, got {len(rows)}"


def test_every_row_has_outcome_and_reason() -> None:
    rows = _table_rows()
    for row in rows:
        # Columns: #, Partner, Vertical, Joined, Outcome, Plan, ARR, Reason
        assert len(row) >= 8, f"row too narrow: {row}"
        outcome = row[4]
        reason = row[7]
        assert outcome in VALID_OUTCOMES, f"row {row[0]} has bad outcome {outcome!r}"
        assert reason and reason != "—", (
            f"row {row[0]} ({row[1]}) is missing a reason: {reason!r}"
        )


def test_at_least_six_conversions() -> None:
    rows = _table_rows()
    converted = [r for r in rows if r[4] == "CONVERTED"]
    assert len(converted) >= 6, (
        f"plan target is ≥ 6 paid conversions; got {len(converted)}"
    )


def test_churn_reasons_are_actionable() -> None:
    """Each churned row references either a tracker story, a roadmap
    milestone, or a documented re-engagement plan."""
    rows = _table_rows()
    actionable = re.compile(
        r"S\d{3}|Voice-2\.0|Q1 2026|warm re-engage|win-back|no product fit|not in roadmap",
        re.IGNORECASE,
    )
    for row in rows:
        if row[4] != "CHURNED":
            continue
        assert actionable.search(row[7]), (
            f"churn reason for {row[1]} is not actionable: {row[7]!r}"
        )


def test_doc_includes_signoff_and_taxonomy() -> None:
    body = LAUNCH_DOC.read_text(encoding="utf-8")
    assert "Sign-off" in body
    assert "Churn reasons — taxonomy" in body
    assert "Booked ARR" in body
