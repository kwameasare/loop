#!/usr/bin/env python3
"""Validate infra/oncall/schedule.yaml against PagerDuty module expectations."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from typing import Any

import yaml

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _parse_iso8601(raw: str) -> bool:
    try:
        dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate_schedule(path: Path) -> list[str]:
    errors: list[str] = []
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return ["schedule payload must be a mapping"]

    team = payload.get("team")
    if not isinstance(team, str) or not team.strip():
        errors.append("team must be a non-empty string")

    timezone = payload.get("timezone")
    if not isinstance(timezone, str) or not timezone.strip():
        errors.append("timezone must be a non-empty string")

    rotations = payload.get("rotations")
    if not isinstance(rotations, list) or not rotations:
        errors.append("rotations must be a non-empty list")
        rotations = []

    rotation_names: set[str] = set()
    for idx, rotation in enumerate(rotations, start=1):
        if not isinstance(rotation, dict):
            errors.append(f"rotation #{idx} must be a mapping")
            continue
        name = rotation.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"rotation #{idx} name must be non-empty")
            continue
        if name in rotation_names:
            errors.append(f"rotation name duplicated: {name}")
        rotation_names.add(name)

        start = rotation.get("start")
        if not isinstance(start, str) or not _parse_iso8601(start):
            errors.append(f"rotation {name} start must be ISO8601 (got {start!r})")

        turn_length = rotation.get("turn_length_hours")
        if not isinstance(turn_length, int) or turn_length <= 0:
            errors.append(f"rotation {name} turn_length_hours must be a positive integer")

        users = rotation.get("users")
        if not isinstance(users, list) or not users:
            errors.append(f"rotation {name} users must be a non-empty list")
            continue
        for user in users:
            if not isinstance(user, str) or not EMAIL_RE.match(user):
                errors.append(f"rotation {name} has invalid user email: {user!r}")

    escalation = payload.get("escalation")
    if not isinstance(escalation, list) or not escalation:
        errors.append("escalation must be a non-empty list")
        escalation = []

    for idx, rule in enumerate(escalation, start=1):
        if not isinstance(rule, dict):
            errors.append(f"escalation rule #{idx} must be a mapping")
            continue
        delay = rule.get("delay_minutes")
        target = rule.get("target")
        if not isinstance(delay, int) or delay < 0:
            errors.append(f"escalation rule #{idx} delay_minutes must be a non-negative integer")
        if not isinstance(target, str) or target not in rotation_names:
            errors.append(
                f"escalation rule #{idx} target must reference a known rotation (got {target!r})"
            )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--schedule",
        type=Path,
        default=Path("infra/oncall/schedule.yaml"),
        help="Path to schedule YAML",
    )
    args = parser.parse_args(argv)

    errors = validate_schedule(args.schedule)
    if errors:
        for error in errors:
            print(f"oncall-schedule: {error}")
        print("oncall-schedule: FAILED")
        return 1

    print("oncall-schedule: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
