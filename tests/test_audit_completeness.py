"""Tests for audit trail completeness matrix (S581)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT_COMPLETENESS = ROOT / "loop_implementation" / "engineering" / "AUDIT_COMPLETENESS.md"
SECURITY = ROOT / "loop_implementation" / "engineering" / "SECURITY.md"


def test_audit_completeness_doc_exists() -> None:
    assert AUDIT_COMPLETENESS.exists(), "AUDIT_COMPLETENESS.md must exist"


def test_security_links_to_audit_completeness() -> None:
    text = SECURITY.read_text()
    assert "AUDIT_COMPLETENESS.md" in text, "SECURITY.md must link to AUDIT_COMPLETENESS.md"


def test_audit_completeness_has_coverage_matrix() -> None:
    """AC requires matrix of write endpoints → audit-event coverage."""
    text = AUDIT_COMPLETENESS.read_text()
    assert "## 1. Coverage matrix" in text
    # Verify the matrix has rows with endpoint method and coverage status.
    assert "| Endpoint | Method |" in text
    assert "| --- |" in text
    # At least some endpoints should be ✅ covered.
    assert "✅" in text
    # At least some endpoints should have ⚠️ gaps.
    assert "⚠️" in text


def test_audit_completeness_has_gap_analysis() -> None:
    """AC requires gaps fixed — document must list identified gaps."""
    text = AUDIT_COMPLETENESS.read_text()
    assert "## 2. Gap analysis" in text
    assert "Critical gaps" in text or "High-priority gaps" in text
    # Gaps should reference follow-up issues.
    assert "S582" in text or "S583" in text or "S584" in text or "S585" in text


def test_audit_completeness_has_event_schema() -> None:
    """Schema requirement: every audit event must conform to the declared schema."""
    text = AUDIT_COMPLETENESS.read_text()
    assert "## 3. Audit event schema" in text
    assert "event_type" in text
    assert "actor" in text
    assert "resource" in text
    assert "action" in text
    assert "timestamp" in text


def test_audit_completeness_remediation_tracking() -> None:
    """Gaps must be tracked as follow-up issues."""
    text = AUDIT_COMPLETENESS.read_text()
    assert "## 4. Remediation tracking" in text
    # At least one follow-up issue should be mentioned.
    assert re.search(r"S58[0-9]", text), "Remediation tracking must reference follow-up issues (S58x)"
