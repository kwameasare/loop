#!/usr/bin/env bash
# scripts/cleanup_agent_worktree.sh — remove a finished agent's worktree.
#
# Run after the agent's last story has merged and its session has ended.
# Refuses to remove a worktree that has uncommitted changes or unpushed
# commits — those are evidence of work-in-flight that would be lost.
#
# Usage:
#   ./scripts/cleanup_agent_worktree.sh <agent-id>
#       Removes ../bot-<agent-id>/ and prunes the corresponding
#       agent/<agent-id>/scratch branch if fully merged into main.
#
#   ./scripts/cleanup_agent_worktree.sh <agent-id> --force
#       Removes even with uncommitted changes or unpushed commits.
#       USE WITH CARE: meant for cleanup after a confirmed crash.

set -euo pipefail

if [[ ${1:-} == "" ]]; then
  echo "usage: $0 <agent-id> [--force]" >&2
  exit 2
fi

AGENT_ID="$1"
FORCE="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PARENT_DIR="$(dirname "$MAIN_ROOT")"
WORKTREE_PATH="$PARENT_DIR/bot-$AGENT_ID"
SCRATCH_BRANCH="agent/$AGENT_ID/scratch"

if [[ ! -e "$WORKTREE_PATH" ]]; then
  echo "cleanup: $WORKTREE_PATH does not exist — nothing to do."
  exit 0
fi

cd "$MAIN_ROOT"

# Liveness checks
if [[ "$FORCE" != "--force" ]]; then
  pushd "$WORKTREE_PATH" > /dev/null
  if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "cleanup: $WORKTREE_PATH has uncommitted changes." >&2
    echo "         Commit/push or pass --force to discard." >&2
    popd > /dev/null
    exit 1
  fi
  unpushed=$(git log --oneline @{u}..HEAD 2>/dev/null || true)
  if [[ -n "$unpushed" ]]; then
    echo "cleanup: $WORKTREE_PATH has unpushed commits:" >&2
    echo "$unpushed" | sed 's/^/  /' >&2
    echo "         Push or pass --force to discard." >&2
    popd > /dev/null
    exit 1
  fi
  popd > /dev/null
fi

echo "cleanup: removing worktree $WORKTREE_PATH"
git worktree remove "$WORKTREE_PATH" ${FORCE:+--force}

# Prune the scratch branch if fully merged into main.
if git show-ref --verify --quiet "refs/heads/$SCRATCH_BRANCH"; then
  if git merge-base --is-ancestor "$SCRATCH_BRANCH" origin/main 2>/dev/null; then
    echo "cleanup: deleting fully-merged branch $SCRATCH_BRANCH"
    git branch -d "$SCRATCH_BRANCH"
  else
    echo "cleanup: keeping branch $SCRATCH_BRANCH (not fully merged into origin/main)"
    echo "         delete manually with: git branch -D $SCRATCH_BRANCH"
  fi
fi

echo "cleanup: done."
