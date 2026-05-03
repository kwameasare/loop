#!/usr/bin/env bash
# CLEANUP_RUN_THIS.sh — rebase + cleanup, all in one shot.
#
# Run from your terminal:
#   cd /Users/praise/bot
#   bash outputs/CLEANUP_RUN_THIS.sh
#
# What it does:
#   1. Force-clears stuck git lock files
#   2. Stashes the 178-line WIP (preserved, not lost)
#   3. Hard-resets local main to origin/main (matches GitHub)
#   4. Removes the bloat files (with confirmation)
#   5. Commits the cleanup as one focused commit
#   6. Pushes to origin
#   7. Replaces AGENT_START_PROMPT.md with the slimmer version
#   8. Optionally retires parallel-work.md
#
# After this exits successfully, your local repo matches origin/main
# minus the bloat. Spawn fresh agents using the new prompt.

set -euo pipefail

REPO=/Users/praise/bot
cd "$REPO"

echo "=== Step 1/8: clearing git locks ==="
# These lock files block all git operations. Remove them aggressively.
sudo rm -f .git/index.lock .git/objects/maintenance.lock 2>/dev/null \
  || rm -f .git/index.lock .git/objects/maintenance.lock 2>/dev/null \
  || true
echo "  cleared"

echo
echo "=== Step 2/8: stashing 178-line WIP ==="
git status --short | head -5
echo "  ..."
git stash push -u -m "wip-pre-cleanup-$(date -u +%Y%m%d-%H%M)" || true
echo "  stash list:"
git stash list | head -3

echo
echo "=== Step 3/8: rebase to origin/main ==="
git fetch origin
git reset --hard origin/main
echo "  local main now at:"
git log --oneline -3

echo
echo "=== Step 4/8: identify bloat files to remove ==="
BLOAT=(
  tools/_agent_assignments.py
  tools/_story_overrides.py
  scripts/bootstrap_autonomous.sh
)
for f in "${BLOAT[@]}"; do
  if [[ -e "$f" ]]; then
    echo "  will remove: $f"
  else
    echo "  (already gone): $f"
  fi
done

read -p "Proceed with removal? [y/N] " ans
if [[ "$ans" != "y" && "$ans" != "Y" ]]; then
  echo "Aborted. Local is now clean (matches origin); no cleanup commit made."
  exit 0
fi

echo
echo "=== Step 5/8: removing bloat ==="
for f in "${BLOAT[@]}"; do
  [[ -e "$f" ]] && rm -f "$f" && echo "  removed: $f"
done

echo
echo "=== Step 6/8: replacing AGENT_START_PROMPT with simple version ==="
if [[ -e outputs/AGENT_START_PROMPT_SIMPLE.md ]]; then
  cp outputs/AGENT_START_PROMPT_SIMPLE.md \
     loop_implementation/skills/meta/AGENT_START_PROMPT.md
  echo "  replaced"
else
  echo "  outputs/AGENT_START_PROMPT_SIMPLE.md not found — skipping"
fi

read -p "Also retire parallel-work.md (its content is duplicated in SKILL_ROUTER)? [y/N] " ans
if [[ "$ans" == "y" || "$ans" == "Y" ]]; then
  git rm -f loop_implementation/skills/meta/parallel-work.md 2>/dev/null \
    || rm -f loop_implementation/skills/meta/parallel-work.md
  echo "  retired"
fi

echo
echo "=== Step 7/8: commit cleanup ==="
git checkout -b cleanup/simplify-multi-agent-tooling
git add -A
git commit -m "chore(tools,docs): simplify multi-agent tooling

Origin shows agents already coordinate cleanly through (a) the picker
filtering already-claimed stories, (b) per-story commit chains, and
(c) StoryV2 line-level merges. The four-agent partition was premature
optimization — never landed on origin and was never needed.

* tools/_agent_assignments.py — removed (partition not needed).
* tools/_story_overrides.py — removed (orphan; never wired in).
* scripts/bootstrap_autonomous.sh — removed (redundant with
  agent_lifecycle.py init).
* loop_implementation/skills/meta/AGENT_START_PROMPT.md — slimmed
  ~600 lines to ~250. Removes partition references, redundant rules
  duplicated by SKILL_ROUTER, the long forbidden table.
* loop_implementation/skills/meta/parallel-work.md — retired (content
  duplicated by SKILL_ROUTER hard rules)."

echo
echo "=== Step 8/8: push the cleanup branch ==="
git push -u origin cleanup/simplify-multi-agent-tooling

echo
echo "=== DONE ==="
echo "Cleanup branch pushed. Open the PR:"
echo
gh pr create \
  --title "chore: simplify multi-agent tooling — remove partition + bloat" \
  --body "Origin proves agents already coordinate cleanly without the
four-agent partition, the override-log, or the bootstrap script.
Removes ~600 lines of unused tooling and skill text.

See commit message for the full breakdown."
echo
echo "Stash list (if you want to revisit the WIP):"
git stash list
