"""Append-only overrides log for story status/owner/notes.

Why this file exists
====================
Stories in ``tools/_stories_v2.py`` are the immutable backlog — title,
sprint, epic, points, priority, AC. They never change after a sprint is
planned. What DOES change is who's working on a story and what state
it's in: claim → checkpoint(s) → close.

Putting that mutation back into ``_stories_v2.py`` would mean N agents
all editing the same Python source file. Two agents claiming adjacent
stories would race on the same byte range; close-after-checkpoint would
mean two writes to one StoryV2 line. Merge conflicts would dominate.

This file is the alternative: an append-only event log. Every claim,
checkpoint, and close emits one tuple appended at the bottom. Two agents
claiming different stories append to different lines — trivial 3-way
merge. Two agents claiming the SAME story append to the same line —
that's a true conflict, exactly the safety we want (whichever PR merges
first wins; the loser re-picks).

Data shape
==========
Each entry is::

    Override(
        story_id="S119",
        status="In progress",
        owner="claude-a",
        notes="...full structured Notes block...",
        ts="2026-04-30T14:00Z",   # for human/audit; loader doesn't read this
    )

Latest entry per ``story_id`` wins when ``build_tracker.py`` overlays
the log on top of the base StoryV2 backlog. Older entries stay in place
forever — they're the audit trail.

Authoring
=========
Agents NEVER edit this file by hand. They call::

    python tools/agent_lifecycle.py claim S119
    python tools/agent_lifecycle.py checkpoint S119 --step 2/5 --note "..."
    python tools/agent_lifecycle.py close S119

Each subcommand appends exactly one Override row to OVERRIDE_LOG, then
commits + pushes through normal git flow. The lifecycle tool is the
ONLY supported writer.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Override:
    story_id: str
    status: str
    owner: str
    notes: str
    ts: str  # ISO-8601 UTC, for audit only


# ─────────────────────────────────────────────────────────────────────
# Append below. Never modify existing rows. Latest row per story_id
# wins. The agent_lifecycle.py tool is the canonical writer.
# ─────────────────────────────────────────────────────────────────────
OVERRIDE_LOG: list[Override] = [
]


__all__ = ["Override", "OVERRIDE_LOG"]
