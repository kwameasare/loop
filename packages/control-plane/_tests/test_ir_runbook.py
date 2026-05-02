"""Tests for the incident-response runbook and game-day log — S806.

AC: runbook checked in; first game-day held; recorded; gaps tracked.
"""

from __future__ import annotations

from pathlib import Path

IR_RUNBOOK = (
    Path(__file__).parent.parent.parent.parent
    / "loop_implementation"
    / "engineering"
    / "INCIDENT_RESPONSE_RUNBOOK.md"
)
GAME_DAY_LOG = (
    Path(__file__).parent.parent.parent.parent
    / "loop_implementation"
    / "engineering"
    / "GAME_DAY_LOG.md"
)

REQUIRED_RUNBOOK_SECTIONS = [
    "## 1.",  # Purpose and scope
    "## 2.",  # Roles
    "## 3.",  # Immediate actions
    "## 4.",  # Diagnosis
    "## 5.",  # Mitigation
    "## 6.",  # Escalation
    "## 7.",  # Resolution
    "## 8.",  # PIR
    "## 9.",  # Game-day cadence
]

REQUIRED_RUNBOOK_ROLES = [
    "Incident commander",
    "Tech lead",
    "Comms lead",
    "Scribe",
]

REQUIRED_SEVERITY_LEVELS = ["SEV1", "SEV2", "SEV3"]


# ---------------------------------------------------------------------------
# Runbook structure tests
# ---------------------------------------------------------------------------


def test_ir_runbook_exists() -> None:
    assert IR_RUNBOOK.exists(), f"Runbook not found: {IR_RUNBOOK}"


def test_ir_runbook_has_required_sections() -> None:
    content = IR_RUNBOOK.read_text()
    missing = [s for s in REQUIRED_RUNBOOK_SECTIONS if s not in content]
    assert not missing, f"IR runbook is missing sections: {missing}"


def test_ir_runbook_defines_all_roles() -> None:
    content = IR_RUNBOOK.read_text()
    missing = [r for r in REQUIRED_RUNBOOK_ROLES if r not in content]
    assert not missing, f"IR runbook is missing role definitions: {missing}"


def test_ir_runbook_references_all_severity_levels() -> None:
    content = IR_RUNBOOK.read_text()
    missing = [s for s in REQUIRED_SEVERITY_LEVELS if s not in content]
    assert not missing, f"IR runbook does not reference severity levels: {missing}"


def test_ir_runbook_includes_rollback_procedure() -> None:
    content = IR_RUNBOOK.read_text()
    assert "rollback" in content.lower(), "IR runbook must include a rollback procedure"


def test_ir_runbook_references_pir() -> None:
    content = IR_RUNBOOK.read_text()
    assert "post-incident review" in content.lower() or "PIR" in content, (
        "IR runbook must reference post-incident review process"
    )


def test_ir_runbook_references_game_day_log() -> None:
    content = IR_RUNBOOK.read_text()
    assert "GAME_DAY_LOG" in content, "IR runbook must link to GAME_DAY_LOG.md"


# ---------------------------------------------------------------------------
# Game-day log tests
# ---------------------------------------------------------------------------


def test_game_day_log_exists() -> None:
    assert GAME_DAY_LOG.exists(), f"Game-day log not found: {GAME_DAY_LOG}"


def test_game_day_log_has_at_least_one_session() -> None:
    content = GAME_DAY_LOG.read_text()
    # Look for a data row (not the header)
    rows = [line for line in content.splitlines() if line.startswith("| GD-")]
    assert rows, "Game-day log must have at least one recorded session (GD-001)"


def test_game_day_log_records_outcome() -> None:
    content = GAME_DAY_LOG.read_text()
    assert "Pass" in content or "Fail" in content or "Partial" in content, (
        "Each game-day session must record an Outcome (Pass/Fail/Partial)"
    )


def test_game_day_log_has_gap_tracker() -> None:
    content = GAME_DAY_LOG.read_text()
    assert "Gap tracker" in content or "gap tracker" in content.lower(), (
        "Game-day log must include a gap tracker section"
    )


def test_game_day_log_gaps_have_owners() -> None:
    content = GAME_DAY_LOG.read_text()
    # Check gap rows reference an engineer or owner token
    gap_rows = [
        line
        for line in content.splitlines()
        if line.startswith("| LOOP-") or line.startswith("| gap-")
    ]
    for row in gap_rows:
        assert "Eng#" in row or "@" in row or "Sec eng" in row or "CTO" in row, (
            f"Gap tracker row must have an owner: {row}"
        )


def test_game_day_log_references_ir_runbook() -> None:
    content = GAME_DAY_LOG.read_text()
    assert "INCIDENT_RESPONSE_RUNBOOK" in content, "Game-day log must link back to the IR runbook"
