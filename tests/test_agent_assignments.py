"""Lock the agent → story-set partition.

Failure modes this guards against:
  * a SID in two agent queues (parallel races on the same line)
  * a SID assigned but not present in _stories_v2 / tracker
  * a SID both assigned and in HUMAN_ONLY
  * a Not-started, agent-doable story that nobody owns (silent backlog)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from _agent_assignments import (  # type: ignore[import-not-found]
    ASSIGNMENTS,
    HUMAN_ONLY,
    all_assigned_ids,
)


def _load_stories() -> list[dict[str, str]]:
    payload = json.loads(
        (ROOT / "loop_implementation" / "tracker" / "tracker.json").read_text()
    )
    return payload["stories"]


def test_assignments_are_disjoint() -> None:
    """No SID may appear in two agent queues."""
    seen: dict[str, str] = {}
    for agent, sids in ASSIGNMENTS.items():
        for sid in sids:
            assert sid not in seen, (
                f"{sid} is assigned to both {seen[sid]} and {agent}"
            )
            seen[sid] = agent


def test_assignments_disjoint_from_human_only() -> None:
    overlap = all_assigned_ids() & HUMAN_ONLY
    assert overlap == set(), f"SIDs both assigned and HUMAN_ONLY: {overlap}"


def test_every_assigned_sid_exists() -> None:
    """An assignment must point at a real StoryV2."""
    real = {s["id"] for s in _load_stories()}
    for agent, sids in ASSIGNMENTS.items():
        for sid in sids:
            assert sid in real, f"{agent} owns {sid} but no such StoryV2"


def test_every_human_only_sid_exists() -> None:
    real = {s["id"] for s in _load_stories()}
    for sid in HUMAN_ONLY:
        assert sid in real, f"HUMAN_ONLY references unknown SID {sid}"


def test_every_pending_story_is_partitioned() -> None:
    """Every Not-started or Blocked story must be either assigned or HUMAN_ONLY.

    Otherwise it's invisible to all four agents — silent backlog.
    """
    pending = {
        s["id"]
        for s in _load_stories()
        if s["status"] in {"Not started", "Blocked"}
    }
    covered = all_assigned_ids() | HUMAN_ONLY
    orphans = pending - covered
    assert orphans == set(), (
        f"pending stories not in any agent queue and not HUMAN_ONLY: "
        f"{sorted(orphans)} — assign them in tools/_agent_assignments.py"
    )
