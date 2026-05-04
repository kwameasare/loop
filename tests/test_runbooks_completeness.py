"""Regression checks for runbook completion and required response fields."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOKS = ROOT / "loop_implementation" / "engineering" / "RUNBOOKS.md"

REQUIRED_IDS = [
    "RB-001",
    "RB-002",
    "RB-003",
    "RB-004",
    "RB-005",
    "RB-006",
    "RB-007",
    "RB-008",
    "RB-010",
    "RB-012",
    "RB-013",
    "RB-014",
    "RB-015",
    "RB-016",
    "RB-017",
    "RB-018",
    "RB-020",
    "RB-024",
]

REQUIRED_FIELDS = [
    "Symptoms / alert fire",
    "First 5-minute triage",
    "Mitigation",
    "Recovery validation",
    "Drill cadence + last drilled date",
]


def _section(text: str, runbook_id: str) -> str:
    pattern = re.compile(rf"^## {re.escape(runbook_id)}.*?(?=^## RB-|\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(text)
    assert match, f"missing section for {runbook_id}"
    return match.group(0)


def test_runbook_index_no_longer_contains_tbd_placeholders() -> None:
    text = RUNBOOKS.read_text()

    assert "TBD M" not in text


def test_required_runbooks_have_operational_response_fields() -> None:
    text = RUNBOOKS.read_text()

    for runbook_id in REQUIRED_IDS:
        section = _section(text, runbook_id)
        for field in REQUIRED_FIELDS:
            assert field in section, f"{runbook_id} missing '{field}'"
