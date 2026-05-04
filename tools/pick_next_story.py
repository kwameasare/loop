#!/usr/bin/env python3
"""tools/pick_next_story.py — recommend the next bite-sized story for an agent.

Used by autonomous coding agents to pick a story to claim. Reads
``loop_implementation/tracker/tracker.json`` (regen via ``build_tracker.py``
first if you've edited the source). Filters and ranks stories so that
multiple agents running in parallel are unlikely to step on each other.

Filter rules
============
A story is *eligible* if and only if:

1. ``status == "Not started"``
2. Every story id referenced as ``[extends Sxxx]`` in its notes is itself
   ``Done`` (transitive deps).
3. The story is in a sprint marked ``Not started`` or ``In progress``.
4. The story's epic isn't on the operator's ``--avoid-epic`` list.
5. (Optional with ``--avoid-hot-files``) The story does not touch a small
   set of hot shared files that current claims also touch — reduces
   merge-conflict risk when many agents are active.

Ranking (lowest first wins)
===========================
1. Priority numeric (P0 < P1 < P2 < P3)
2. Sprint-id numeric (S2 < S3 < ... ; closed sprints excluded)
3. Story-id numeric (S100 < S101 < ...)
4. Number of currently-claimed stories that touch the same hot files (lower
   first; spreads load away from contention)
5. Stable: alphabetical id

Output
======
Default: a single line with the story id.
``--json``: a JSON blob with metadata for the agent to use directly.
``--n=K``: top K candidates instead of just the top 1.
``--dry-run``: no side effects (this script never writes anyway, but the
flag is here for symmetry with future variants).

Atomicity
=========
This script *recommends* — it does not reserve. Final atomicity comes from
PR-merge order: if two agents claim the same story at once, the second PR
hits a merge conflict on ``tools/_stories_v2.py`` and the loser is told to
re-pick. See ``loop_implementation/skills/meta/parallel-work.md``.

Exit codes
==========
* 0 — picked at least one story (printed)
* 2 — no eligible story available (the operator's filters are too tight,
  every story is claimed, or the project is finished)
* 3 — tracker.json is missing / unreadable (regen with build_tracker.py)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
TRACKER_JSON = ROOT / "loop_implementation" / "tracker" / "tracker.json"

# Local import for the per-agent partition.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _agent_assignments import ASSIGNMENTS, HUMAN_ONLY

# Files that many stories touch — picking a story that doesn't conflict
# with the in-flight set reduces wasted work from merge conflicts.
HOT_FILES = (
    "tools/build_tracker.py",
    "tools/_stories_v2.py",
    "loop_implementation/data/SCHEMA.md",
    "loop_implementation/engineering/ENV_REFERENCE.md",
    "loop_implementation/engineering/ERROR_CODES.md",
    "loop_implementation/api/openapi.yaml",
    "apps/studio/src/lib/cp-api/generated.ts",
)

EXTENDS_RE = re.compile(r"\[extends\s+(S\d{3})", re.IGNORECASE)
PRIO_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def _load() -> dict[str, Any]:
    if not TRACKER_JSON.exists():
        print(
            f"pick_next_story: {TRACKER_JSON} missing — run "
            f"`python tools/build_tracker.py` first.",
            file=sys.stderr,
        )
        sys.exit(3)
    return json.loads(TRACKER_JSON.read_text())


def _sprint_rank(sprint_id: str) -> int:
    """Return numeric rank for sprint id (S0/S1/.../S37). Closed-sprint
    stories are filtered out elsewhere; rank used for ordering only."""
    try:
        return int(sprint_id.lstrip("S"))
    except ValueError:
        return 9999


def _story_num(story_id: str) -> int:
    try:
        return int(story_id.lstrip("S"))
    except ValueError:
        return 9999


def _extends(notes: str) -> set[str]:
    return set(EXTENDS_RE.findall(notes or ""))


def _claimed_now(stories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stories under any open claim (In progress / Handing off / Blocked)."""
    return [
        s
        for s in stories
        if s["status"] in {"In progress", "Handing off", "Blocked"}
    ]


def _hot_files_in_play(claimed: list[dict[str, Any]]) -> set[str]:
    """Best-effort heuristic: for each currently-claimed story, infer
    which hot files it likely touches. We just take the union of hot
    files mentioned in the claim's notes (which agents fill in as
    'Branch:', 'Last step:', 'Commits:'). Imperfect but cheap.

    Agents that want a sharper avoidance signal can pass the explicit
    hot-files-touched list via ``--seen-hot-file``.
    """
    seen: set[str] = set()
    for s in claimed:
        for hf in HOT_FILES:
            if hf in (s.get("notes") or ""):
                seen.add(hf)
    return seen


def _story_likely_touches(story: dict[str, Any], hot: set[str]) -> int:
    """Heuristic: how many hot files might this story touch?

    Looks for hot-file names mentioned in the story title or notes.
    Returns a count (0+) — used as a tiebreaker, not a hard filter.
    """
    text = f"{story.get('title','')}\n{story.get('notes','')}"
    return sum(1 for hf in hot if hf in text)


def _eligible(
    story: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    closed_sprints: set[str],
    avoid_epics: set[str],
    assigned_set: frozenset[str] | None,
) -> bool:
    if story["status"] != "Not started":
        return False
    if story["id"] in HUMAN_ONLY:
        return False
    if assigned_set is not None and story["id"] not in assigned_set:
        return False
    if story["sprint"] in closed_sprints:
        return False
    if story["epic"] in avoid_epics:
        return False
    for dep_id in _extends(story.get("notes") or ""):
        dep = by_id.get(dep_id)
        if dep is None:
            # Unknown dep id — treat as not-yet-shipped. Conservative.
            return False
        if dep["status"] != "Done":
            return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Pick a bite-sized story to claim. See "
            "loop_implementation/skills/meta/parallel-work.md."
        )
    )
    ap.add_argument(
        "--owner",
        default="agent",
        help="Agent identity (e.g. 'github-copilot', 'claude-code'). "
        "Used only for context-aware preferences.",
    )
    ap.add_argument(
        "--prefer-epic",
        action="append",
        default=[],
        help="Prefer stories on this epic id (e.g. E2). Repeatable.",
    )
    ap.add_argument(
        "--prefer-sprint",
        action="append",
        default=[],
        help="Prefer stories in this sprint id (e.g. S2). Repeatable.",
    )
    ap.add_argument(
        "--avoid-epic",
        action="append",
        default=[],
        help="Skip stories on this epic id. Repeatable.",
    )
    ap.add_argument(
        "--avoid-hot-files",
        action="store_true",
        help="Penalize stories that look like they'll touch hot files "
        "currently in play. Cheap heuristic, not a hard exclusion.",
    )
    ap.add_argument(
        "--assigned-to",
        default=None,
        help="Filter to stories assigned to this agent in "
        "tools/_agent_assignments.py (e.g. codex-orion, codex-vega, "
        "copilot-thor, copilot-titan). Unknown ids match the empty set.",
    )
    ap.add_argument(
        "--n",
        type=int,
        default=1,
        help="Print top N candidates instead of just the top one (default: 1).",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON object/array with metadata instead of just ids.",
    )
    args = ap.parse_args()

    data = _load()
    stories: list[dict[str, Any]] = data["stories"]
    sprints: list[dict[str, Any]] = data["sprints"]

    by_id = {s["id"]: s for s in stories}
    closed_sprints = {s["id"] for s in sprints if s["status"] == "Done"}
    avoid_epics = set(args.avoid_epic)

    assigned_set: frozenset[str] | None = None
    if args.assigned_to:
        assigned_set = ASSIGNMENTS.get(args.assigned_to, frozenset())

    eligible = [
        s for s in stories
        if _eligible(s, by_id, closed_sprints, avoid_epics, assigned_set)
    ]
    if not eligible:
        msg = (
            "pick_next_story: no eligible story matches the current filters."
        )
        if args.assigned_to:
            msg += (
                f" --assigned-to={args.assigned_to} narrows the picker to "
                f"that agent's queue (size: "
                f"{len(ASSIGNMENTS.get(args.assigned_to, frozenset()))}); "
                "every story in the queue may already be Done, In progress, "
                "or Blocked behind unshipped [extends Sxxx] deps. Run "
                "`python tools/agent_lifecycle.py status` to confirm, then "
                "exit cleanly via `agent_lifecycle.py teardown`."
            )
        else:
            msg += (
                " Either every backlog story has unshipped deps or the "
                "project is finished. Try relaxing --avoid-epic or run "
                "`python tools/build_tracker.py` to refresh the tracker."
            )
        print(msg, file=sys.stderr)
        return 2

    # Hot-file conflict heuristic.
    hot_in_play: set[str] = (
        _hot_files_in_play(_claimed_now(stories)) if args.avoid_hot_files else set()
    )

    prefer_epics = set(args.prefer_epic)
    prefer_sprints = set(args.prefer_sprint)

    def rank(s: dict[str, Any]) -> tuple:
        return (
            0 if s["epic"] in prefer_epics else 1,
            0 if s["sprint"] in prefer_sprints else 1,
            PRIO_RANK.get(s["priority"], 9),
            _sprint_rank(s["sprint"]),
            _story_num(s["id"]),
            _story_likely_touches(s, hot_in_play),
            s["id"],
        )

    eligible.sort(key=rank)
    picks = eligible[: max(1, args.n)]

    if args.json:
        payload = [
            {
                "id": s["id"],
                "title": s["title"],
                "sprint": s["sprint"],
                "epic": s["epic"],
                "points": s["points"],
                "priority": s["priority"],
                "ac": s["notes"],
                "extends": sorted(_extends(s.get("notes") or "")),
            }
            for s in picks
        ]
        print(
            json.dumps(payload[0] if args.n == 1 else payload, indent=2)
        )
    else:
        for s in picks:
            print(s["id"])

    return 0


if __name__ == "__main__":
    sys.exit(main())
