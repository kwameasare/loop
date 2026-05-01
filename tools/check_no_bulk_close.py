#!/usr/bin/env python3
"""tools/check_no_bulk_close.py — flag batch-grind commit patterns.

Multi-agent rule (SKILL_ROUTER §16, post-2026-04 revision): the bar is
*full implementation per story*, not commit count. Multiple bite-sized
stories MAY be closed in a single PR or commit when they share a file,
a skill, or one coherent diff — e.g. ``feat(security): PASETO v4.local
encode + decode (S105, S106)``. What's still forbidden is the
batch-grind anti-pattern that historically masked stub-shipping:

  * Commit titles of the form ``pass<N> close <K> stories`` (the literal
    pattern that produced 4863-line stub-batches).
  * Commit titles of the form ``close <K> stories`` (literal numeric
    count instead of substance description).
  * Closing ≥4 distinct stories in one commit — at that scale the
    "natural unit" framing is implausible.

Usage:
    python tools/check_no_bulk_close.py --base <ref> --head <ref>

Exit:
    0 — clean
    1 — batch-grind pattern detected (printed)
    2 — usage error
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

BULK_PATTERNS = (
    re.compile(r"\bpass\s*\d+\s+close\s+\d+\s+stor(?:y|ies)\b", re.IGNORECASE),
    re.compile(r"\bclose\s+\d+\s+stor(?:y|ies)\b", re.IGNORECASE),
)
STORY_ID_RE = re.compile(r"\bS\d{3}\b")
CLOSE_VERBS_RE = re.compile(
    r"\b(close|closing|closed|complete|completes|completed|done)\b",
    re.IGNORECASE,
)


def _git(*args: str) -> str:
    out = subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    )
    return out.stdout


def _commits(base: str, head: str) -> list[tuple[str, str]]:
    raw = _git("log", "--format=%H%x09%s", f"{base}..{head}")
    pairs: list[tuple[str, str]] = []
    for line in raw.splitlines():
        if "\t" in line:
            sha, subj = line.split("\t", 1)
            pairs.append((sha.strip(), subj.strip()))
    return pairs


def _is_bulk_close(subject: str) -> tuple[bool, str]:
    # 1) Literal batch-grind tells: `pass<N> close <K> stories` or
    #    `close <K> stories`. These are the historical signatures of
    #    stub-shipping passes; rename the commit to describe substance.
    for pat in BULK_PATTERNS:
        m = pat.search(subject)
        if m:
            return True, f"matches batch-grind pattern {pat.pattern!r}"

    # 2) Closing ≥4 distinct stories in a single commit — at that scale
    #    the "natural unit" framing is implausible. 1-3 in one commit
    #    is fine when the work is genuinely combinable (e.g.
    #    "feat(security): PASETO encode + decode (S105, S106)").
    ids = STORY_ID_RE.findall(subject)
    if len(set(ids)) >= 4 and CLOSE_VERBS_RE.search(subject):
        return (
            True,
            f"closes {len(set(ids))} stories in one commit: {sorted(set(ids))} — "
            "at ≥4 stories per commit the unit isn't a natural combination; "
            "split into smaller PRs or merge the stories into one larger story",
        )
    return False, ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True, help="git ref to compare from")
    ap.add_argument("--head", required=True, help="git ref to compare to")
    args = ap.parse_args()

    offenders: list[tuple[str, str, str]] = []
    for sha, subject in _commits(args.base, args.head):
        is_bulk, why = _is_bulk_close(subject)
        if is_bulk:
            offenders.append((sha, subject, why))

    if not offenders:
        print("no-bulk-close: clean — no commit closes more than one story.")
        return 0

    print(
        "no-bulk-close: BATCH-GRIND COMMIT PATTERNS DETECTED.\n"
        "Combining naturally combinable stories in one commit is fine — but\n"
        "the patterns flagged below are batch-grind tells, not natural\n"
        "combinations. Either rename the commit to describe substance\n"
        "(e.g. `feat(security): PASETO encode + decode (S105, S106)`) or\n"
        "split into smaller commits. See SKILL_ROUTER.md hard rule §16 and\n"
        "skills/meta/parallel-work.md.\n",
        file=sys.stderr,
    )
    for sha, subj, why in offenders:
        print(f"  ✗ {sha[:8]}  «{subj}»\n      {why}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
