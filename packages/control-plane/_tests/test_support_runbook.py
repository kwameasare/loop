"""
Tests for S658 — support runbook + ticketing integration (Front).

Validates:
- SUPPORT_RUNBOOK.md structure and content
- support@ email routing is documented
- routing rules are present and numbered
- SLA tiers are defined
- escalation paths are described
- RB-025 runbook exists with required fields
"""

from pathlib import Path
import re
import pytest

RUNBOOK_PATH = Path("loop_implementation/engineering/SUPPORT_RUNBOOK.md")


@pytest.fixture(scope="module")
def content() -> str:
    assert RUNBOOK_PATH.exists(), f"{RUNBOOK_PATH} not found"
    return RUNBOOK_PATH.read_text()


# ── File existence ─────────────────────────────────────────────────────────

def test_support_runbook_file_exists():
    assert RUNBOOK_PATH.exists()


# ── Inbound channels ───────────────────────────────────────────────────────

def test_support_email_documented(content):
    assert "support@loop.ai" in content


def test_billing_email_documented(content):
    assert "billing@loop.ai" in content


def test_security_email_documented(content):
    assert "security@loop.ai" in content


def test_front_inbox_mentioned(content):
    assert "Loop Support" in content or "Front" in content


# ── Routing rules ──────────────────────────────────────────────────────────

def test_routing_rules_section_present(content):
    assert "Routing rules" in content or "routing rules" in content


def test_at_least_five_routing_rules(content):
    # SR-001 … SR-005 must all appear
    for i in range(1, 6):
        assert f"SR-{i:03d}" in content, f"SR-{i:03d} missing"


def test_billing_routing_rule_documented(content):
    assert "billing" in content.lower()


def test_security_routing_rule_documented(content):
    assert "security" in content.lower()


def test_cve_routing_rule_documented(content):
    assert "CVE" in content


# ── SLA targets ────────────────────────────────────────────────────────────

def test_sla_section_present(content):
    assert "SLA" in content


def test_enterprise_sla_defined(content):
    assert "Enterprise" in content or "enterprise" in content


def test_sla_first_response_defined(content):
    assert "First response" in content or "first response" in content


def test_sla_business_hours_mentioned(content):
    assert "business hour" in content


# ── Escalation paths ───────────────────────────────────────────────────────

def test_escalation_section_present(content):
    assert "Escalation" in content or "escalation" in content


def test_technical_escalation_documented(content):
    assert "needs-engineering" in content or "technical escalation" in content.lower()


def test_security_escalation_documented(content):
    # Security escalation must reference the security runbook or PagerDuty
    assert "PagerDuty" in content or "SECURITY.md" in content


def test_billing_escalation_documented(content):
    assert "billing-escalation" in content or "Billing" in content


# ── RB-025 runbook ─────────────────────────────────────────────────────────

def test_rb025_exists(content):
    assert "RB-025" in content


def test_rb025_has_owner(content):
    idx = content.index("RB-025")
    section = content[idx: idx + 800]
    assert "Owner" in section or "owner" in section


def test_rb025_has_steps(content):
    idx = content.index("RB-025")
    section = content[idx: idx + 1200]
    assert "Steps" in section or "steps" in section


def test_rb025_has_sev_target(content):
    idx = content.index("RB-025")
    section = content[idx: idx + 600]
    assert "SEV" in section


# ── Smoke test command ─────────────────────────────────────────────────────

def test_smoke_test_curl_command_present(content):
    assert "curl" in content


def test_smoke_test_references_front_api(content):
    assert "frontapp.com" in content or "FRONT_API_TOKEN" in content
