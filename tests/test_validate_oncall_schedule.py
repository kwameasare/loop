"""Unit checks for tools/validate_oncall_schedule.py."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import validate_oncall_schedule as validator  # type: ignore[import-not-found]


def test_validator_accepts_committed_schedule() -> None:
    errors = validator.validate_schedule(ROOT / "infra" / "oncall" / "schedule.yaml")
    assert errors == []


def test_validator_rejects_unknown_escalation_target(tmp_path: Path) -> None:
    schedule = tmp_path / "schedule.yaml"
    schedule.write_text(
        """
team: loop
timezone: UTC
rotations:
  - name: primary
    start: "2026-05-04T00:00:00Z"
    turn_length_hours: 24
    users: [person@loop.local]
escalation:
  - delay_minutes: 0
    target: tertiary
""".strip(),
        encoding="utf-8",
    )

    errors = validator.validate_schedule(schedule)
    assert any("target must reference a known rotation" in err for err in errors)
