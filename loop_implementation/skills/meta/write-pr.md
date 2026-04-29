---
name: write-pr
description: Use when opening a pull request. Always runs after the primary task skill.
when_to_use: |
  - Opening any PR.
required_reading:
  - engineering/HANDBOOK.md      # §3 PR conventions
  - AGENTS.md                    # PR examples + before-merge checklist
applies_to: meta
owner: PR author
last_reviewed: 2026-04-29
---

# Write PR

## Trigger

Always when opening a pull request.

## Required reading

`engineering/HANDBOOK.md` §3.

## Steps

1. **Verify the tracker claim is in your branch.** The first commit of the branch should be `chore(tracker): claim S0NN`. If it isn't, run `meta/update-tracker.md` BEFORE phase first.
2. **Title:** Conventional Commit. Examples:
   - `feat(runtime): add graceful degrade on budget cap`
   - `fix(channel-slack): verify signature timestamp window`
   - `docs(architecture): clarify episodic memory replication`
   - `feat(sdk)!:` (with `!`) for breaking changes.
3. **Body sections:**
   - **What & why** — one paragraph, why this change exists. The diff shows what.
   - **Changes** — bullet list of touched files/areas (not every line).
   - **Testing** — what was added; how to reproduce verification.
   - **Story** — link to the tracker story (`tracker/IMPLEMENTATION_TRACKER.xlsx`). Format: `Closes S0NN`.
   - **Migration / breaking** — call out if any.
   - **Screenshots** — for any UI change.
4. **Run `meta/update-tracker.md` AFTER phase NOW** (before opening the PR for review):
   - Edit `tools/build_tracker.py` to flip your story's status to `Done` + add `PR #<number> (<date>)` to the notes cell.
   - Regenerate: `python tools/build_tracker.py && python tools/tracker_to_machine.py && python scripts/recalc.py tracker/IMPLEMENTATION_TRACKER.xlsx`.
   - Commit as the **LAST** commit of the branch. Title: `chore(tracker): close S0NN`.
5. **Pre-merge checklist** (paste into the PR body and check before merge):
   - [ ] Tracker `claim S0NN` (or `resume S0NN`) commit is the first commit on this branch.
   - [ ] Checkpoint commits exist for any task that took > 1 h (`chore(tracker): checkpoint S0NN step <N>/<M>`).
   - [ ] Tracker `close S0NN` commit is the last commit on this branch.
   - [ ] Notes cell on the closing tracker entry uses the canonical structured format.
   - [ ] Tests pass (unit + integration).
   - [ ] Lint + typecheck clean.
   - [ ] No cloud SDK imported in forbidden packages.
   - [ ] Story ID referenced in PR body (`Closes S0NN`).
   - [ ] Docs updated in the same PR.
   - [ ] No secrets in diff (pre-commit detect-secrets passed).
   - [ ] Eval suite passed (runtime PRs).
   - [ ] Bench non-regressed (hot-path PRs).
6. **Review request:**
   - Tag the package owner from `architecture/ARCHITECTURE.md` §11.
   - For cross-cutting changes, tag every affected owner.
7. **Squash merge** into `main`. No merge commits. Clean commit message = the PR title.
8. **If rolled back later:** apply `meta/update-tracker.md` to flip the story back to `In progress` or `Blocked` immediately, in a `chore(tracker): reopen S0NN` PR.

## Definition of done

- [ ] Conventional Commit title.
- [ ] Body has What/Why/Changes/Testing/Story.
- [ ] Pre-merge checklist filled.
- [ ] Right reviewers tagged.
- [ ] Squash-merged.
- [ ] Tracker `claim` commit is FIRST on the branch.
- [ ] Tracker `close` commit is LAST on the branch.
- [ ] All four tracker outputs (xlsx + md + json + csv) regenerated and committed.

## Anti-patterns

- ❌ Title that's not a Conventional Commit.
- ❌ Body that says "see diff."
- ❌ Skipping the breaking-change `!`.
- ❌ Big multi-feature PR. Split.
- ❌ Doc follow-ups in a separate PR.

## Related skills

- `meta/update-tracker.md`.

## References

- `engineering/HANDBOOK.md` §3.
- `AGENTS.md`.
