"""Tests for DR tabletop record (S575)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLETOP = ROOT / "loop_implementation" / "engineering" / "DR_TABLETOP.md"
DR_DOC = ROOT / "loop_implementation" / "engineering" / "DR.md"


def test_tabletop_doc_exists() -> None:
    assert TABLETOP.exists()


def test_dr_links_to_tabletop() -> None:
    text = DR_DOC.read_text()
    assert "DR_TABLETOP.md" in text


def test_tabletop_has_at_least_one_recorded_exercise() -> None:
    """SOC2 CC7.5 evidence requires at least one exercise on file before
    the doc counts. We assert the §4 section contains a dated entry that
    matches the exercise format (`### 4.M — Tabletop YYYY-MM-DD …`).
    """
    text = TABLETOP.read_text()
    matches = re.findall(r"^### 4\.\d+ — Tabletop \d{4}-\d{2}-\d{2}", text, re.MULTILINE)
    assert matches, "expected at least one recorded tabletop entry"


def test_tabletop_has_required_sections() -> None:
    text = TABLETOP.read_text()
    for section in ("## 1. Roles", "## 2. Scenario contract",
                    "## 3. Standing scoring rubric", "## 4. Exercise minutes",
                    "## 5. How to run a new tabletop", "## 6. Compliance mapping"):
        assert section in text, f"missing section: {section}"


def test_tabletop_records_gaps_with_owners() -> None:
    """AC requires gaps to be tracked. We enforce that the recorded
    exercise lists at least one DR-GAP-N entry with an owner, so the
    template stays honest.
    """
    text = TABLETOP.read_text()
    gaps = re.findall(r"\*\*DR-GAP-\d+\*\*.*?\*Owner:\* [^.]+", text, re.DOTALL)
    assert gaps, "expected at least one DR-GAP-N entry with an owner"
