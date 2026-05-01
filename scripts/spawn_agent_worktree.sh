#!/usr/bin/env bash
# scripts/spawn_agent_worktree.sh — create an isolated worktree for one agent.
#
# Multi-agent setup: each local-running coding agent gets its own working
# directory backed by `git worktree`. The agent's IDE / CLI is pointed at
# that directory. `git checkout` in one worktree no longer disturbs the
# others (the only constraint is that two worktrees can't check out the
# same branch simultaneously — which is exactly the safety we want).
#
# Usage:
#   ./scripts/spawn_agent_worktree.sh <agent-id>
#       Creates ../bot-<agent-id>/ off latest origin/main, prints the path.
#
#   ./scripts/spawn_agent_worktree.sh <agent-id> --pick
#       Same, plus runs `pick_next_story.py` inside the new worktree
#       and prints the recommended story id.
#
# After this exits, point the agent's tool at the printed PATH:
#   * Claude Code: `claude --workdir <PATH>` or open the folder
#   * Cursor: File → Open Folder → <PATH>
#   * VS Code + Copilot: code <PATH>
#   * Aider: cd <PATH> && aider
#   * GitHub Copilot Coding Agent: cloud-hosted, doesn't use this script —
#     it spins its own sandbox per task.
#
# Cleanup is via scripts/cleanup_agent_worktree.sh after the agent's last
# story merges and the agent exits.

set -euo pipefail

if [[ ${1:-} == "" ]]; then
  echo "usage: $0 <agent-id> [--pick]" >&2
  echo "  agent-id: stable identifier (e.g. claude-a, copilot-b)" >&2
  exit 2
fi

AGENT_ID="$1"
shift || true

if [[ ! "$AGENT_ID" =~ ^[a-z][a-z0-9-]{1,30}$ ]]; then
  echo "spawn: agent-id must be lowercase, start with a letter, ≤32 chars" >&2
  echo "       (got: '$AGENT_ID')" >&2
  exit 2
fi

# This script lives in scripts/ inside the main worktree; resolve the repo
# root and put the new worktree as a sibling of it.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PARENT_DIR="$(dirname "$MAIN_ROOT")"
WORKTREE_PATH="$PARENT_DIR/bot-$AGENT_ID"

if [[ -e "$WORKTREE_PATH" ]]; then
  echo "spawn: $WORKTREE_PATH already exists." >&2
  echo "       If a worktree from a previous session is stale, run:" >&2
  echo "         scripts/cleanup_agent_worktree.sh $AGENT_ID" >&2
  echo "       first." >&2
  exit 1
fi

# Refuse to spawn if the operator has uncommitted changes in main —
# avoids the agent inheriting half-finished local edits.
cd "$MAIN_ROOT"
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "spawn: main worktree at $MAIN_ROOT has uncommitted changes." >&2
  echo "       Commit or stash before spawning a new agent." >&2
  exit 1
fi

# Always start the worktree at the freshest origin/main.
echo "spawn: fetching origin..."
git fetch --quiet origin

# Each agent's worktree starts on a per-agent scratch branch; the agent
# will branch off it for each story it claims (per AGENT_START_PROMPT.md).
SCRATCH_BRANCH="agent/$AGENT_ID/scratch"

# If the scratch branch already exists upstream or locally, reuse it.
if git show-ref --verify --quiet "refs/heads/$SCRATCH_BRANCH"; then
  echo "spawn: reusing existing local branch $SCRATCH_BRANCH"
  git worktree add "$WORKTREE_PATH" "$SCRATCH_BRANCH"
elif git show-ref --verify --quiet "refs/remotes/origin/$SCRATCH_BRANCH"; then
  echo "spawn: tracking origin/$SCRATCH_BRANCH"
  git worktree add --track -b "$SCRATCH_BRANCH" \
      "$WORKTREE_PATH" "origin/$SCRATCH_BRANCH"
else
  echo "spawn: creating new branch $SCRATCH_BRANCH off origin/main"
  git worktree add -b "$SCRATCH_BRANCH" "$WORKTREE_PATH" origin/main
fi

echo
echo "spawn: ready."
echo "       Worktree:    $WORKTREE_PATH"
echo "       Branch:      $SCRATCH_BRANCH"
echo "       Main repo:   $MAIN_ROOT (unchanged)"
echo

if [[ ${1:-} == "--pick" ]]; then
  echo "spawn: picking next story for $AGENT_ID..."
  cd "$WORKTREE_PATH"
  python3 tools/pick_next_story.py --owner "$AGENT_ID" --json
  echo
fi

cat <<EOF
Next steps for the operator:
  1. Open $WORKTREE_PATH in the agent's IDE/CLI.
  2. Paste loop_implementation/skills/meta/AGENT_START_PROMPT.md as the
     start prompt, replacing <your-id> with: $AGENT_ID
  3. The agent's first command should be:
        cd $WORKTREE_PATH
        python tools/pick_next_story.py --owner $AGENT_ID --json
  4. When the agent's last story merges and the session ends, clean up:
        scripts/cleanup_agent_worktree.sh $AGENT_ID
EOF
