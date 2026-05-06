"""Validate the canonical UX/UI cycle story partition."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from _agent_assignments_ux import (  # type: ignore[import-not-found]
    ASSIGNMENTS_UX,
    START_FIRST_AGENT,
    START_FIRST_STORIES,
    all_assigned_ids,
    all_story_ids,
    duplicate_assignments,
    missing_dependency_ids,
    unassigned_ids,
)
from _stories_ux import UX_STORIES, blocking_foundation_ids  # type: ignore[import-not-found]


def test_every_ux_story_is_assigned_once() -> None:
    assert unassigned_ids() == frozenset()
    assert duplicate_assignments() == {}
    assert all_assigned_ids() == all_story_ids()


def test_every_dependency_points_at_real_story() -> None:
    assert missing_dependency_ids() == {}


def test_start_first_gate_is_explicit_and_owned_by_orion() -> None:
    assert START_FIRST_AGENT == "codex-orion"
    assert START_FIRST_STORIES == blocking_foundation_ids()
    assert START_FIRST_STORIES <= ASSIGNMENTS_UX["codex-orion"]


def test_every_story_has_execution_metadata() -> None:
    for story in UX_STORIES:
        assert story.id.startswith("UX")
        assert story.title
        assert story.phase
        assert story.area
        assert story.points in {1, 2, 3}
        assert story.priority in {"P0", "P1", "P2", "P3"}
        assert story.canonical_sections
        assert story.skills
        assert story.primary_paths
        assert story.acceptance.startswith("AC: ")
