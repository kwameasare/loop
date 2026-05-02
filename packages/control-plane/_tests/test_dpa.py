"""Tests for DPA template (DPA.md) and redlines workflow (DPA_REDLINES.md).

We validate document structure, presence of required legal clauses, Annex
completeness, and the redlines workflow definition.
"""

import re
from pathlib import Path

ENGINEERING_DIR = Path(__file__).parent.parent.parent.parent / "loop_implementation" / "engineering"
DPA_PATH = ENGINEERING_DIR / "DPA.md"
REDLINES_PATH = ENGINEERING_DIR / "DPA_REDLINES.md"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _dpa_text() -> str:
    return DPA_PATH.read_text()


def _redlines_text() -> str:
    return REDLINES_PATH.read_text()


# ---------------------------------------------------------------------------
# DPA.md — file existence and basic structure
# ---------------------------------------------------------------------------


def test_dpa_file_exists():
    assert DPA_PATH.exists(), "DPA.md must exist in loop_implementation/engineering/"


def test_dpa_has_title():
    text = _dpa_text()
    assert "Data Processing Agreement" in text


def test_dpa_has_definitions_section():
    assert "### 1. Definitions" in _dpa_text()


def test_dpa_defines_personal_data():
    assert "Personal Data" in _dpa_text()


def test_dpa_defines_sub_processor():
    assert "Sub-processor" in _dpa_text()


def test_dpa_has_controller_instructions_section():
    assert "### 3. Controller" in _dpa_text()


def test_dpa_has_security_section():
    text = _dpa_text()
    assert "### 5. Security" in text


def test_dpa_has_sub_processing_section():
    assert "### 6. Sub-processing" in _dpa_text()


def test_dpa_has_breach_notification_section():
    assert "### 8. Data Breach Notification" in _dpa_text()


def test_dpa_has_72h_breach_notification_sla():
    """GDPR Article 33 requires notification within 72 hours."""
    text = _dpa_text()
    assert "72 hour" in text.lower() or "72-hour" in text.lower(), (
        "DPA must specify 72-hour breach notification SLA"
    )


def test_dpa_has_audit_rights_section():
    assert "### 11. Audit Rights" in _dpa_text()


def test_dpa_has_international_transfers_section():
    assert "### 12. International Data Transfers" in _dpa_text()


def test_dpa_references_sccs():
    """DPA must reference Standard Contractual Clauses for cross-border transfers."""
    assert "SCCs" in _dpa_text() or "Standard Contractual Clauses" in _dpa_text()


# ---------------------------------------------------------------------------
# DPA.md — Annexes completeness
# ---------------------------------------------------------------------------


def test_dpa_has_annex_i_processing_activities():
    assert "Annex I" in _dpa_text()


def test_dpa_has_annex_ii_toms():
    text = _dpa_text()
    assert "Annex II" in text
    assert "Technical and Organisational Measures" in text or "TOM" in text


def test_dpa_annex_ii_covers_encryption_at_rest():
    assert "Encryption at rest" in _dpa_text() or "AES-256" in _dpa_text()


def test_dpa_annex_ii_covers_access_control():
    assert "Access control" in _dpa_text() or "access control" in _dpa_text()


def test_dpa_has_data_deletion_clause():
    text = _dpa_text()
    assert "delet" in text.lower()


def test_dpa_has_contact_email():
    """DPA must include a privacy contact email."""
    assert "privacy@loop.ai" in _dpa_text()


# ---------------------------------------------------------------------------
# DPA_REDLINES.md — file existence and structure
# ---------------------------------------------------------------------------


def test_redlines_file_exists():
    assert REDLINES_PATH.exists(), "DPA_REDLINES.md must exist"


def test_redlines_has_roles_section():
    assert "## Roles" in _redlines_text()


def test_redlines_defines_legal_reviewer_role():
    assert "Legal Reviewer" in _redlines_text()


def test_redlines_defines_security_reviewer_role():
    assert "Security Reviewer" in _redlines_text()


def test_redlines_has_pr_naming_convention():
    text = _redlines_text()
    assert "dpa-redlines-" in text or "Branch naming" in text


def test_redlines_has_sla():
    """Workflow must state an SLA for initial redline response."""
    text = _redlines_text()
    assert re.search(r"\d+\s*business days", text), (
        "DPA_REDLINES.md must specify a business-day SLA"
    )


def test_redlines_has_sample_closed_pr():
    """Workflow document must include a sample/closed redline PR."""
    text = _redlines_text()
    assert "Sample Redline PR" in text or "sample" in text.lower()


def test_redlines_references_dpa():
    assert "DPA.md" in _redlines_text()


def test_redlines_has_escalation_section():
    assert "## Escalation" in _redlines_text()
