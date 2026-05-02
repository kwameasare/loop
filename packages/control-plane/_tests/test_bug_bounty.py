"""Tests for bug_bounty.py -- S809: bug-bounty program launch."""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime, timedelta

import pytest
from loop_control_plane.bug_bounty import (
    BountyProgram,
    ReportDecision,
    ReportSeverity,
    TriageError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)


def _populate_three_clean_reports(program: BountyProgram) -> None:
    """Submit, ack within 24 h, and decide within 5 bd for 3 reports."""
    for i in range(3):
        submitted = NOW + timedelta(hours=i * 48)
        rid = program.submit(f"H1-00{i + 1}", submitted_at=submitted)
        program.acknowledge(rid, acked_at=submitted + timedelta(hours=2))
        program.decide(
            rid,
            decision=ReportDecision.VALID,
            severity=ReportSeverity.MEDIUM,
            decided_at=submitted + timedelta(days=3),
        )


# ---------------------------------------------------------------------------
# BountyReport fields
# ---------------------------------------------------------------------------


def test_new_report_is_not_acknowledged() -> None:
    program = BountyProgram()
    rid = program.submit("H1-001", submitted_at=NOW)
    assert not program.report(rid).is_acknowledged


def test_acknowledge_sets_timestamp() -> None:
    program = BountyProgram()
    rid = program.submit("H1-001", submitted_at=NOW)
    program.acknowledge(rid, acked_at=NOW + timedelta(hours=1))
    assert program.report(rid).acknowledged_at == NOW + timedelta(hours=1)


def test_ack_sla_met_when_within_24h() -> None:
    program = BountyProgram()
    rid = program.submit("H1-001", submitted_at=NOW)
    program.acknowledge(rid, acked_at=NOW + timedelta(hours=23))
    assert program.report(rid).ack_sla_met() is True


def test_ack_sla_violated_when_after_24h() -> None:
    program = BountyProgram()
    rid = program.submit("H1-001", submitted_at=NOW)
    program.acknowledge(rid, acked_at=NOW + timedelta(hours=25))
    assert program.report(rid).ack_sla_met() is False


def test_triage_sla_met_when_within_7_days() -> None:
    program = BountyProgram()
    rid = program.submit("H1-001", submitted_at=NOW)
    program.acknowledge(rid, acked_at=NOW + timedelta(hours=1))
    program.decide(rid, decision=ReportDecision.VALID, decided_at=NOW + timedelta(days=5))
    assert program.report(rid).triage_sla_met() is True


def test_triage_sla_violated_when_after_7_days() -> None:
    program = BountyProgram()
    rid = program.submit("H1-001", submitted_at=NOW)
    program.acknowledge(rid, acked_at=NOW + timedelta(hours=1))
    program.decide(rid, decision=ReportDecision.VALID, decided_at=NOW + timedelta(days=8))
    assert program.report(rid).triage_sla_met() is False


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_double_ack_raises_triage_error() -> None:
    program = BountyProgram()
    rid = program.submit("H1-001", submitted_at=NOW)
    program.acknowledge(rid, acked_at=NOW + timedelta(hours=1))
    with pytest.raises(TriageError, match="already acknowledged"):
        program.acknowledge(rid, acked_at=NOW + timedelta(hours=2))


def test_decide_without_ack_raises_triage_error() -> None:
    program = BountyProgram()
    rid = program.submit("H1-001", submitted_at=NOW)
    with pytest.raises(TriageError, match="must be acknowledged"):
        program.decide(rid, decision=ReportDecision.NA, decided_at=NOW)


def test_double_decide_raises_triage_error() -> None:
    program = BountyProgram()
    rid = program.submit("H1-001", submitted_at=NOW)
    program.acknowledge(rid, acked_at=NOW + timedelta(hours=1))
    program.decide(rid, decision=ReportDecision.DUPLICATE, decided_at=NOW + timedelta(days=1))
    with pytest.raises(TriageError, match="already has a decision"):
        program.decide(rid, decision=ReportDecision.VALID, decided_at=NOW + timedelta(days=2))


def test_unknown_report_id_raises_triage_error() -> None:
    from uuid import uuid4

    program = BountyProgram()
    with pytest.raises(TriageError, match="Unknown report"):
        program.acknowledge(uuid4(), acked_at=NOW)


# ---------------------------------------------------------------------------
# is_live
# ---------------------------------------------------------------------------


def test_program_not_live_before_three_reports() -> None:
    program = BountyProgram()
    assert not program.is_live


def test_program_live_after_three_clean_reports() -> None:
    program = BountyProgram()
    _populate_three_clean_reports(program)
    assert program.is_live


def test_program_not_live_when_sla_violated() -> None:
    program = BountyProgram()
    # 3 reports but one has a triage SLA violation
    for i in range(2):
        submitted = NOW + timedelta(hours=i * 48)
        rid = program.submit(f"H1-00{i + 1}", submitted_at=submitted)
        program.acknowledge(rid, acked_at=submitted + timedelta(hours=1))
        program.decide(rid, decision=ReportDecision.VALID, decided_at=submitted + timedelta(days=2))

    # Third report with SLA violation
    submitted = NOW + timedelta(hours=200)
    rid = program.submit("H1-003", submitted_at=submitted)
    program.acknowledge(rid, acked_at=submitted + timedelta(hours=1))
    program.decide(rid, decision=ReportDecision.VALID, decided_at=submitted + timedelta(days=10))
    assert not program.is_live


# ---------------------------------------------------------------------------
# SLA violations
# ---------------------------------------------------------------------------


def test_sla_violations_empty_for_clean_reports() -> None:
    program = BountyProgram()
    _populate_three_clean_reports(program)
    assert program.sla_violations() == []


def test_sla_violations_detected_for_late_ack() -> None:
    program = BountyProgram()
    rid = program.submit("H1-001", submitted_at=NOW)
    program.acknowledge(rid, acked_at=NOW + timedelta(hours=30))  # > 24 h
    violations = program.sla_violations()
    assert len(violations) == 1
    assert violations[0].stage == "ack"
    assert violations[0].report_id == rid


# ---------------------------------------------------------------------------
# Docs pages
# ---------------------------------------------------------------------------


def test_public_bug_bounty_page_exists() -> None:
    assert pathlib.Path("docs/site/bug-bounty.md").exists()


def test_public_bug_bounty_page_covers_scope_and_payouts() -> None:
    content = pathlib.Path("docs/site/bug-bounty.md").read_text()
    for keyword in ("scope", "bounty", "critical", "sla", "hackerone"):
        assert keyword.lower() in content.lower(), f"{keyword!r} missing from bug-bounty.md"


def test_internal_bug_bounty_ops_doc_exists() -> None:
    assert pathlib.Path("loop_implementation/engineering/BUG_BOUNTY.md").exists()


def test_internal_bug_bounty_ops_doc_has_triage_log() -> None:
    content = pathlib.Path("loop_implementation/engineering/BUG_BOUNTY.md").read_text()
    assert "triage log" in content.lower()
