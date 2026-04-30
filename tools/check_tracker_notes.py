"""Tracker notes lint — enforce structured Notes-cell format on Done stories.

A Done / In progress / Blocked / Handing off story must carry the canonical
fields so any successor agent (different vendor, different shift) can resume
or audit the work mechanically. Bare-prose notes break the resume-task
protocol described in skills/meta/resume-task.md.

Usage:
    python tools/check_tracker_notes.py
    python tools/check_tracker_notes.py --strict   # fail on any drift
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STORIES_CSV = REPO_ROOT / "loop_implementation" / "tracker" / "csv" / "stories.csv"

# Status → required field set on the Notes cell.
REQUIRED_FIELDS: dict[str, frozenset[str]] = {
    "In progress": frozenset({"Branch:", "Skill:", "Last step:", "Heartbeat:"}),
    "Handing off": frozenset({"Branch:", "Skill:", "Last step:", "Heartbeat:"}),
    "Blocked":     frozenset({"Branch:", "Skill:", "Heartbeat:", "Blockers:"}),
    "Done":        frozenset({"PR", "Branch:"}),  # PR # or PR: link; branch reference
}

# Stories where a richer note is not required (CTO setup, hiring, etc.).
SKIP_IDS: frozenset[str] = frozenset({"S002"})


def lint(strict: bool = False) -> int:
    if not STORIES_CSV.exists():
        print(f"error: {STORIES_CSV} not found", file=sys.stderr)
        return 2

    failures: list[str] = []
    with STORIES_CSV.open() as f:
        for row in csv.DictReader(f):
            sid = row["id"]
            status = row["status"]
            notes = row["notes"] or ""

            if sid in SKIP_IDS:
                continue
            if status not in REQUIRED_FIELDS:
                continue

            required = REQUIRED_FIELDS[status]
            missing = sorted(token for token in required if token not in notes)
            if missing:
                failures.append(
                    f"  ✗ {sid} ({status}): missing tokens {missing}\n"
                    f"      first 80 chars of notes: {notes[:80]!r}"
                )

    if not failures:
        print("tracker-notes: all stories satisfy the structured Notes contract.")
        return 0

    print("tracker-notes: structured Notes-cell drift detected:\n", file=sys.stderr)
    for failure in failures:
        print(failure, file=sys.stderr)
    print(
        "\nFix: edit tools/build_tracker.py to populate the canonical Notes "
        "block (Branch / Skill / Last step / Heartbeat / etc.). See "
        "skills/meta/update-tracker.md §'Canonical Notes-cell format'.",
        file=sys.stderr,
    )
    return 1 if strict else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--strict", action="store_true", help="(default — kept for clarity)")
    sys.exit(lint(strict=p.parse_args().strict))
