"""Tests for SOC2 Type 1 attestation kickoff record (S582)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOC2 = ROOT / "loop_implementation" / "engineering" / "SOC2.md"


def test_soc2_doc_exists() -> None:
    assert SOC2.exists(), "SOC2.md must exist"


def test_kickoff_meeting_section_present() -> None:
    text = SOC2.read_text()
    assert "## Kickoff meeting" in text, "SOC2.md must have a Kickoff meeting section"
    assert "2026-05-02" in text, "Kickoff meeting must have a date committed"


def test_evidence_list_present() -> None:
    """AC: evidence list committed."""
    text = SOC2.read_text()
    assert "## Evidence list" in text or "## Evidence list — Type 1 pack" in text
    # At least engineering and people evidence categories.
    assert "Engineering-managed evidence" in text
    assert "People" in text or "P01" in text


def test_audit_window_dates_committed() -> None:
    """AC: window dates committed."""
    text = SOC2.read_text()
    assert "## Audit window" in text or "Audit window & key dates" in text
    # Fieldwork dates must appear.
    assert "2026-07-07" in text, "Fieldwork start date must be committed"
    assert "2026-07-31" in text, "Type 1 report date must be committed"
    assert "2026-08-01" in text, "Type 2 observation window start must be committed"


def test_kickoff_milestone_marked_done() -> None:
    """Kickoff milestone must be ✅ done in milestones table."""
    text = SOC2.read_text()
    assert re.search(r"Kickoff meeting.*✅ done", text), (
        "Key milestones table must mark 'Kickoff meeting held' as ✅ done"
    )


def test_changelog_has_s582_entry() -> None:
    text = SOC2.read_text()
    assert "S582" in text, "Change log must have an S582 entry"
