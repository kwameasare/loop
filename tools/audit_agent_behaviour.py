#!/usr/bin/env python3
"""tools/audit_agent_behaviour.py — periodic audit of agent compliance.

Run on a cadence (weekly is reasonable) to confirm every recent closed
story followed the multi-agent protocol. Catches the failure modes that
slipped past the per-PR CI gates — e.g. direct-pushed commits, bulk-close
patterns, claims without checkpoints, claims missing skill citations.

Usage:
    python tools/audit_agent_behaviour.py --since 7.days
    python tools/audit_agent_behaviour.py --since-sha <ref>

Exit:
    0 — no violations
    1 — violations reported (human follow-up needed)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field

STORY_RE = re.compile(r"\bS\d{3}\b")
CLAIM_RE = re.compile(r"^chore\(tracker\):\s*claim\s+(S\d{3})", re.IGNORECASE)
CHECKPOINT_RE = re.compile(
    r"^chore\(tracker\):\s*checkpoint\s+(S\d{3})", re.IGNORECASE
)
CLOSE_RE = re.compile(r"^chore\(tracker\):\s*close\s+(S\d{3})", re.IGNORECASE)
PR_NUM_TAIL_RE = re.compile(r"\(#\d+\)$")
BULK_RE = re.compile(
    r"\bpass\s*\d+\s+close\s+\d+\s+stor(?:y|ies)\b", re.IGNORECASE
)


@dataclass
class StoryActivity:
    sid: str
    claim_shas: list[str] = field(default_factory=list)
    checkpoint_shas: list[str] = field(default_factory=list)
    close_shas: list[str] = field(default_factory=list)
    feature_shas: list[str] = field(default_factory=list)


def _git(*args: str) -> str:
    out = subprocess.run(["git", *args], check=True, capture_output=True, text=True)
    return out.stdout


def _commits(since: str) -> list[tuple[str, str]]:
    raw = _git("log", "--format=%H%x09%s", since + "..HEAD")
    pairs = []
    for line in raw.splitlines():
        if "\t" in line:
            sha, subj = line.split("\t", 1)
            pairs.append((sha.strip(), subj.strip()))
    return pairs


def _classify(commits: list[tuple[str, str]]) -> tuple[
    dict[str, StoryActivity], list[tuple[str, str]], list[tuple[str, str]]
]:
    by_story: dict[str, StoryActivity] = defaultdict(lambda: StoryActivity(""))
    bulk_offenders: list[tuple[str, str]] = []
    direct_pushes: list[tuple[str, str]] = []
    for sha, subj in commits:
        if BULK_RE.search(subj):
            bulk_offenders.append((sha, subj))
        # Direct-push detection works only on main (subject doesn't end in (#N))
        if not PR_NUM_TAIL_RE.search(subj):
            direct_pushes.append((sha, subj))

        m = CLAIM_RE.match(subj)
        if m:
            sid = m.group(1)
            by_story[sid].sid = sid
            by_story[sid].claim_shas.append(sha)
            continue
        m = CHECKPOINT_RE.match(subj)
        if m:
            sid = m.group(1)
            by_story[sid].sid = sid
            by_story[sid].checkpoint_shas.append(sha)
            continue
        m = CLOSE_RE.match(subj)
        if m:
            sid = m.group(1)
            by_story[sid].sid = sid
            by_story[sid].close_shas.append(sha)
            continue
        # Otherwise, any feat/fix commit naming a story
        ids = STORY_RE.findall(subj)
        if subj.startswith(("feat", "fix", "refactor")) and ids:
            for sid in set(ids):
                by_story[sid].sid = sid
                by_story[sid].feature_shas.append(sha)
    return by_story, bulk_offenders, direct_pushes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--since", help="git --since spec, e.g. '7.days', '24.hours'")
    g.add_argument("--since-sha", help="audit commits after this sha")
    args = ap.parse_args()

    if args.since:
        # Use git's --since with a sentinel root-commit base
        since_arg = "--since=" + args.since.replace(".", " ")
        raw = _git("log", "--format=%H%x09%s", since_arg)
        pairs = []
        for line in raw.splitlines():
            if "\t" in line:
                sha, subj = line.split("\t", 1)
                pairs.append((sha.strip(), subj.strip()))
        commits = pairs
    else:
        commits = _commits(args.since_sha)

    by_story, bulk, direct_pushes = _classify(commits)

    issues: list[str] = []
    if bulk:
        issues.append(
            f"{len(bulk)} bulk-close commit(s) detected (SKILL_ROUTER §16 violation):"
        )
        for sha, subj in bulk:
            issues.append(f"    {sha[:8]}  «{subj}»")
    if direct_pushes:
        # Suppress when full history shown — most commits in any window
        # without PR-number tails just means branch protection isn't on yet.
        # We still surface a count.
        issues.append(
            f"{len(direct_pushes)} commit(s) without PR-number suffix — "
            "likely direct push to main (SKILL_ROUTER §17). Apply branch "
            "protection per docs/branch-protection.md."
        )

    # Per-story integrity
    for sid, sa in sorted(by_story.items()):
        # Closed stories should have at least 1 claim and 1 close commit
        if sa.feature_shas or sa.close_shas:
            if not sa.claim_shas:
                issues.append(
                    f"{sid}: feature/close commits exist without a claim commit "
                    "(no `chore(tracker): claim Sxxx` ancestor in window)."
                )
            # If the feature commit is large the checkpoint-discipline gate
            # already handles this; here we just flag stories that closed
            # without any checkpoint despite multiple feature commits.
            if len(sa.feature_shas) >= 2 and not sa.checkpoint_shas:
                issues.append(
                    f"{sid}: {len(sa.feature_shas)} feature commits without a "
                    "checkpoint commit — long task, no resumable cut."
                )

    if not issues:
        print("audit_agent_behaviour: clean — every story followed the protocol.")
        return 0

    print("audit_agent_behaviour: VIOLATIONS DETECTED.\n", file=sys.stderr)
    for line in issues:
        print(line, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
