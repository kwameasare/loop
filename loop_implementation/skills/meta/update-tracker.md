---
name: update-tracker
description: Use to update story status in the implementation tracker. Mandatory before starting work (claim), during work (blockers), and after completing work (done). Also use when adding a new story or shifting sprints.
when_to_use: |
  BEFORE starting a task — claim the story (status: in_progress, owner: you).
  DURING a task — mark blockers (status: blocked, with note).
  AFTER completing a task — mark done (status: completed, link the PR).
  Whenever a new story emerges or the sprint plan shifts.
required_reading:
  - tracker/TRACKER.md
  - tracker/SPRINT_0.md
  - AGENTS.md
applies_to: meta
owner: PM (when hired) / CTO (interim) / every agent for own work
last_reviewed: 2026-04-29
---

# Update tracker

## Trigger

The tracker is the team's coordination mechanism. **Every task touches it three times:**

1. **Before** you start work (claim the story).
2. **During** the task (only if blocked or scope changes).
3. **After** the task (mark done, link the PR).

If the tracker doesn't reflect what you're doing, the rest of the team is flying blind.

## Required reading

`tracker/TRACKER.md` to find your story's current state.

---

## The tracker lifecycle (mandatory protocol)

### Phase 1: BEFORE — claim the story

Run this **before writing any code**.

1. Open `tracker/TRACKER.md` and find the story for your task. If no story exists, **stop** and either:
   - Pick the closest existing story (most likely path), or
   - Create a new story (see "Add a new story" below) and reference it. Don't start work without one.
2. **Check for an existing claim.** If your story is already `In progress` (someone else's Owner), do NOT double-claim. Apply `meta/resume-task.md` instead — you're taking over, not starting fresh. Only proceed past this step if status is `Not started` or the existing claim is stale (> 4 h since last heartbeat for AI agents; > 7 d for humans).
3. Confirm it's not marked `Blocked` without an unblocking story.
4. **Claim** it by editing `tools/build_tracker.py`. The Notes cell follows the canonical structured format so a future agent can resume:
   ```python
   # find your story in the stories list
   ("S0NN", "...", "agent-bot",  "S0",  "EX",  ..., ..., "In progress",
    "**Active.**\n"
    "Branch: agent-bot/<short-slug>\n"
    "Skill: skills/<category>/<name>.md\n"
    "Last step: 0/<M> (just claimed)\n"
    "Heartbeat: 2026-04-30T14:00Z (<agent-identity>)\n"
    "Open questions: none\n"
    "Blockers: none\n"
    "Commits: (will accumulate)"),
   ```
   The `<agent-identity>` is your tool name (Claude / Cursor / Codex / Copilot / Aider / human-name) so a successor knows who handed off.
5. Regenerate companions:
   ```bash
   python tools/build_tracker.py
   python tools/tracker_to_machine.py
   python scripts/recalc.py tracker/IMPLEMENTATION_TRACKER.xlsx   # zero formula errors
   ```
6. **Open a "claim" PR** OR **fold the claim edit into your feature PR's first commit**. Either is acceptable; folding is preferred for short stories so the tracker change ships with the feature.
   - If standalone: title `chore(tracker): claim S0NN`. Single commit. Merge fast.
   - If folded: first commit of the feature branch is `chore(tracker): claim S0NN`; the rest is the actual work.
7. **Push immediately.** A claimed story without a pushed branch can't be resumed by another agent. Always `git push` after the claim commit.

### Phase 2: DURING — heartbeat checkpoints + status changes

#### 2a. Heartbeat checkpoints (mandatory for tasks > 1 h)

Long tasks commit partial progress at logical boundaries so any other agent (different vendor, different shift, post-rate-limit) can resume:

- **After every numbered step** in the skill you're applying, or every ~30 min — whichever comes first — commit:
  ```bash
  git commit -am "chore(tracker): checkpoint S0NN step <N>/<M> — <one-line summary>"
  git push
  ```
- **Update the Notes cell** at each checkpoint with the new `Last step:` and `Heartbeat:` lines. Regenerate the four companions and amend that into the checkpoint commit (or push as the next commit).
- **No uncommitted work.** Before any pause longer than 30 min, commit and push WIP:
  ```bash
  git commit -am "chore(tracker): wip S0NN — paused at <reason>"
  git push
  ```

Without checkpoints, an interrupted task can't be resumed cleanly — your work-in-progress lives on a single workstation that the successor agent can't see.

#### 2b. Status changes (only when something changes)

You only flip status mid-task if:

- **You're blocked.** Flip status to `Blocked`, fill out the structured notes block with `Blockers:` populated, push, hand the story back to the queue.
- **Scope changed materially.** Original story is wrong (bigger/smaller/different) — close + replace, or split. Note the reason.
- **You're handing off.** Flip status to `Handing off` (or stay `In progress` if the next agent picks up immediately). Set Owner blank. Push.

Otherwise, don't churn the tracker mid-task. Keep working.

Quick blocker workflow:

```python
# in tools/build_tracker.py
("S0NN", "...", "agent-bot",  "S0",  "EX",  ..., ..., "Blocked",
 "**Blocked.**\n"
 "Branch: agent-bot/runtime-graceful-degrade\n"
 "Skill: skills/coding/implement-runtime-feature.md\n"
 "Last step: 7/12 (memory invariants done)\n"
 "Heartbeat: 2026-04-30T15:00Z (Claude)\n"
 "Blockers:\n"
 "- Need ADR-029 to clarify whether max_iterations counts tool retries.\n"
 "Commits: abc1234, def5678, 90ab12"),
```

Regenerate; push; tag the unblocker.

### Phase 3: AFTER — mark done

Run this **before opening the PR for review**, not after merge:

1. Edit `tools/build_tracker.py` to set status `Done` and write a closing notes block (preserving the audit trail):
   ```python
   ("S0NN", "...", "agent-bot",  "S0",  "EX",  ..., ..., "Done",
    "**Done.**\n"
    "PR: #123 (2026-04-30)\n"
    "Branch: agent-bot/runtime-graceful-degrade (merged + deleted)\n"
    "Skill: skills/coding/implement-runtime-feature.md (all 12 steps complete)\n"
    "Final heartbeat: 2026-04-30T17:30Z (Claude)\n"
    "Notes: <any post-merge ops, e.g. eval cassette refreshed, perf gain measured>"),
   ```
2. Regenerate all five outputs (`build_tracker.py` + `tracker_to_machine.py` + `recalc.py`).
3. Commit the regen output **as the LAST commit** of the feature PR. Title: `chore(tracker): close S0NN`.
4. The PR now contains: claim → checkpoints → close. The whole lifecycle is captured in one branch.

If the merged PR is later **rolled back**, flip the story to `In progress` (or `Blocked`) in a follow-up `chore(tracker): reopen S0NN` PR with a new structured Notes block explaining what failed.

---

## Status canonical values

| Status | When to use |
|--------|-------------|
| `Not started` | Default for new stories. |
| `In progress` | Currently being worked. Owner + structured Notes mandatory. |
| `Handing off` | Active agent stopping; next agent should pick up immediately. Owner blank, structured Notes mandatory. |
| `Blocked` | Cannot progress without external resolution. Notes must include `Blockers:`. |
| `In review` | Code complete, PR open, awaiting review. (Auto-set by CI when PR opens? See "Automation" below.) |
| `Done` | Merged + verified in staging. |
| `Cancelled` | Decision made not to ship. Notes cell must explain. |

Always update the **Notes** cell when changing status, in the structured format (see below). A bare-string Notes cell on an `In progress` story triggers orphan recovery (see `meta/resume-task.md` §6) — wasteful for the next agent.

## Canonical Notes-cell format (mandatory on `In progress`/`Blocked`/`Handing off`)

```
**<Status word>.**             <- Active | Resumed | Handing off | Blocked
Branch: <git-branch>
Skill: skills/<category>/<name>.md
Last step: <N>/<M> (<one-line description of where you paused>)
Heartbeat: <ISO-8601 UTC> (<agent-identity>)
Open questions: <list or "none">
Blockers: <list or "none">
Commits: <short-hash> <commit-message>; <short-hash> ...
```

If a field is empty, write the literal `none` — never omit. The next agent (possibly a different vendor) parses these fields to resume.

---

## Add a new story

If your task has no matching story:

1. Pick the next free `S<NNN>` in the `stories = [...]` list. Never reuse retired numbers.
2. Map it to an existing **Epic ID** (`E<NN>` from the Epics sheet). If no Epic fits, propose a new Epic in the same PR (talk to PM/CTO first if it's a sprint-shift).
3. Estimate **points** (1, 2, 3, 5, 8, 13). Don't break stories that would estimate > 13 — split them.
4. Set **Priority** (P0/P1/P2).
5. Add to the right **Sprint** column.
6. PR title: `chore(tracker): add S0NN — <story title>`. Tag PM + CTO.

---

## Add a new sprint or shift the roadmap

Out of scope for this skill. Apply `architecture/propose-adr.md` if it's a strategic shift; otherwise tag PM/CTO and discuss in `#planning` first.

---

## Source of truth + the four outputs

```
tools/build_tracker.py         ← THE source of truth (edit here)
   │
   ├── IMPLEMENTATION_TRACKER.xlsx   (humans / Excel / Sheets)
   ├── TRACKER.md                    (canonical AI view)
   ├── tracker.json                  (programmatic / agents)
   └── csv/*.csv                     (per sheet)
```

Never edit the xlsx directly. Never edit TRACKER.md, tracker.json, or csv/*.csv directly. Always:

```bash
python tools/build_tracker.py
python tools/tracker_to_machine.py
python scripts/recalc.py tracker/IMPLEMENTATION_TRACKER.xlsx
```

Commit all five outputs. CI rejects PRs where they're out of sync.

---

## Automation (Sprint 1 deliverable)

The first version is hand-driven; CI will help later:

- **PR-open hook** (Sprint 1): when a PR description references `S0NN`, a CI step auto-flips status to `In review` if it's `In progress`.
- **PR-merge hook** (Sprint 1): on merge of a PR closing a story, auto-flips status to `Done`. Falls back to manual when CI can't infer.
- **Heartbeat staleness probe** (Sprint 1): hourly job parses every `In progress` story's structured Notes; if `Heartbeat` is older than the threshold (4 h AI agent, 7 d human), auto-emits a Slack `#orphans` notification so any agent can pick it up.
- **Stale-claim alarm** (Sprint 2): a daily job pings owners of stories `In progress` for >7 days with no PR open.

Until those exist, agents own the tracker manually per the lifecycle above.

---

## Definition of done (for this skill)

- [ ] Story claimed in `tools/build_tracker.py` (status: In progress, owner: you).
- [ ] All five outputs regenerated and committed.
- [ ] `recalc.py` returns zero formula errors.
- [ ] PR title is `chore(tracker): claim/close/reopen/add S0NN — ...`.
- [ ] Notes cell updated (date + reason / PR #).
- [ ] Tag PM/CTO if creating a new story or shifting sprint.

## Anti-patterns

- ❌ Working on a story without claiming it first.
- ❌ Hand-editing the xlsx, TRACKER.md, json, or csv. Always regenerate.
- ❌ Status changes without notes.
- ❌ Reusing a retired story ID.
- ❌ Marking `Done` before the PR is merged.
- ❌ Leaving `In progress` for >7 days without a blocker note.
- ❌ Skipping the tracker because "it's a small change." If it's small, the update is small.

## Related skills

- `meta/write-pr.md` — every feature PR's last commit should close the story.
- `architecture/propose-adr.md` — if scope change is a strategic shift.

## References

- `tracker/TRACKER.md` (current state).
- `tracker/SPRINT_0.md` (sprint 0 plan).
- `tools/build_tracker.py` (source of truth — edit here).
