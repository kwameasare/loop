"""Smoke tests for tools/build_tracker.py — keeps the tracker honest in CI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_tracker  # type: ignore[import-not-found]


def test_validate_passes() -> None:
    """The committed tracker data must be internally consistent."""
    errors = build_tracker.validate()
    assert errors == [], f"tracker validation errors: {errors}"


def test_no_duplicate_story_ids() -> None:
    ids = [s.id for s in build_tracker.STORIES]
    assert len(ids) == len(set(ids)), "duplicate story IDs"


def test_every_story_status_is_valid() -> None:
    for s in build_tracker.STORIES:
        assert s.status in build_tracker.VALID_STATUSES, f"{s.id} has invalid status {s.status!r}"


def test_in_progress_stories_have_structured_notes() -> None:
    required = (
        "Branch:",
        "Skill:",
        "Last step:",
        "Heartbeat:",
        "Open questions:",
        "Blockers:",
        "Commits:",
    )
    for s in build_tracker.STORIES:
        if s.status in {"In progress", "Blocked", "Handing off"}:
            for key in required:
                assert key in s.notes, f"{s.id} (status={s.status}) missing '{key}' in Notes"


def test_render_md_includes_every_story() -> None:
    md = build_tracker.render_md()
    for s in build_tracker.STORIES:
        assert s.id in md, f"{s.id} missing from rendered TRACKER.md"


def test_render_json_round_trips() -> None:
    payload = build_tracker.render_json()
    s = json.dumps(payload)
    parsed = json.loads(s)
    assert parsed["_meta"]["format_version"] == 2
    assert len(parsed["stories"]) == len(build_tracker.STORIES)
    assert len(parsed["epics"]) == len(build_tracker.EPICS)


def test_check_clean_after_regenerate() -> None:
    """Regenerated outputs should match the committed ones (no drift)."""
    build_tracker.write_outputs()
    assert build_tracker.check_clean() == 0
