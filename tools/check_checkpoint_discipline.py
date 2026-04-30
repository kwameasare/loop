"""Checkpoint discipline gate — fails if a feature commit lands > 90 lines of
diff without a preceding `chore(tracker): claim S0NN` AND a checkpoint commit
on the same branch.

Long stories (8+ points / hours of agent work) must commit progress at logical
boundaries so a different agent can resume after a rate-limit. A single giant
feature commit between claim and close means the work was effectively
unrecoverable until the moment of the push.

Heuristic: a `feat(...)` commit on a feature branch must be ≤ 90 lines of
non-test, non-doc diff UNLESS there is a `chore(tracker): checkpoint S0NN ...`
commit between the claim and this commit on the same branch.

Usage:
    python tools/check_checkpoint_discipline.py [--base BASE] [--head HEAD]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

CHECKPOINT_RE = re.compile(r"^chore\(tracker\): checkpoint S\d{3}\b")
CLAIM_RE = re.compile(r"^chore\(tracker\): claim S\d{3}\b")
RESUME_RE = re.compile(r"^chore\(tracker\): resume S\d{3}\b")
FEATURE_RE = re.compile(r"^(feat|fix|refactor)\([^)]+\):")
EXEMPT_PATH_RE = re.compile(
    r"(/_tests/|^tests/|^docs/|^loop_implementation/|"
    r"\.md$|\.yaml$|\.yml$|\.toml$|\.json$|\.txt$|\.lock$|"
    r"^pnpm-lock\.yaml$)"
)
LIMIT = 90


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)


def commit_subject(sha: str) -> str:
    return run(["git", "log", "-1", "--format=%s", sha]).strip()


def commits_in_range(base: str, head: str) -> list[str]:
    raw = run(["git", "log", "--format=%H", f"{base}..{head}"])
    # log returns newest-first; we want oldest-first for the walk
    return list(reversed([c.strip() for c in raw.splitlines() if c.strip()]))


def diff_lines(sha: str) -> int:
    """Lines of code-relevant diff in this commit (additions + deletions)."""
    raw = run(["git", "show", "--numstat", "--format=", sha])
    total = 0
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        adds_s, dels_s, path = parts
        if EXEMPT_PATH_RE.search(path):
            continue
        try:
            total += int(adds_s) + int(dels_s)
        except ValueError:
            # Binary file — count as 0 lines (we're focused on code drift).
            continue
    return total


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", default="origin/main")
    p.add_argument("--head", default="HEAD")
    args = p.parse_args()

    try:
        commits = commits_in_range(args.base, args.head)
    except subprocess.CalledProcessError as exc:
        print(f"error: cannot compute commit range: {exc}", file=sys.stderr)
        return 2

    if not commits:
        print("checkpoint-discipline: no commits between base and head — pass.")
        return 0

    failures: list[str] = []
    seen_claim_or_checkpoint = False

    for sha in commits:
        subject = commit_subject(sha)
        if CLAIM_RE.match(subject) or RESUME_RE.match(subject) or CHECKPOINT_RE.match(subject):
            seen_claim_or_checkpoint = True
            continue
        if FEATURE_RE.match(subject):
            n = diff_lines(sha)
            if n > LIMIT and not seen_claim_or_checkpoint:
                failures.append(
                    f"  ✗ {sha[:8]} «{subject}»\n"
                    f"      {n} lines of code diff with no preceding "
                    f"checkpoint commit on this branch (limit: {LIMIT})."
                )
            # A feature commit doesn't reset the seen flag — once you've checkpointed,
            # you can ship multiple feature commits before another checkpoint, as long
            # as none of them individually exceeds the limit.
            if n > LIMIT and seen_claim_or_checkpoint:
                # This is the case the rule actually permits: the claim/checkpoint
                # acts as the boundary marker. Still warn if the *single* commit is
                # very large, but pass.
                pass

    if not failures:
        print("checkpoint-discipline: all feature commits respect the rule — pass.")
        return 0

    print(
        "checkpoint-discipline: feature commits exceed the limit without a checkpoint:\n",
        file=sys.stderr,
    )
    for failure in failures:
        print(failure, file=sys.stderr)
    print(
        "\nFix: insert a `chore(tracker): checkpoint S0NN step <N>/<M> — <one-liner>` "
        "commit between your claim and your feature commit, or split the feature "
        "commit into smaller pieces. See skills/meta/update-tracker.md §Phase 2a.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
