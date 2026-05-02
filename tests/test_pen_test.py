"""Tests for pen-test preparation document (S576)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PEN_TEST = ROOT / "loop_implementation" / "engineering" / "PEN_TEST.md"
SECURITY = ROOT / "loop_implementation" / "engineering" / "SECURITY.md"


def test_pen_test_doc_exists() -> None:
    assert PEN_TEST.exists(), "PEN_TEST.md must exist"


def test_security_links_to_pen_test() -> None:
    text = SECURITY.read_text()
    assert "PEN_TEST.md" in text, "SECURITY.md must link to PEN_TEST.md"


def test_pen_test_has_required_sections() -> None:
    text = PEN_TEST.read_text()
    sections = [
        "## 1. Vendor selection",
        "## 2. Scope agreement",
        "## 2.1 In-scope systems",
        "## 2.2 Out-of-scope",
        "## 3. Rules of Engagement (RoE)",
        "## 3.1 Testing windows",
        "## 3.2 Communication protocol",
        "## 3.3 Access controls",
        "## 3.4 Defensive posture during testing",
        "## 3.5 Escalation matrix",
        "## 4. Staging environment setup",
        "## 4.1 Provisioning checklist",
        "## 5. Credential management",
        "## 5.1 Pre-test credential issuance",
        "## 5.2 Credential rotation (post-test)",
        "## 6. Appendices",
    ]
    for section in sections:
        assert section in text, f"PEN_TEST.md missing section: {section}"


def test_pen_test_has_escalation_matrix() -> None:
    """AC requires handling findings at different severity levels.
    Verify the escalation matrix is present with P1/P2/P3 rows.
    """
    text = PEN_TEST.read_text()
    assert "| **P1 — Critical**" in text
    assert "| **P2 — High**" in text
    assert "| **P3 — Medium**" in text
    # Verify each has an escalation path and timeline.
    assert "CTO + CEO page" in text
    assert "≤1 h" in text
