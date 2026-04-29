---
name: resume-task
description: Use when picking up an in-progress story another agent abandoned (rate-limited, crashed, vendor swap, shift handover). The new agent reads the structured claim, syncs the branch, replays the skill from the last completed step.
when_to_use: |
  - You are an agent taking over a task another agent started.
  - Before claiming any story, ALWAYS check whether one matching your task is already `In progress` — if yes, you resume it instead of claiming a new one.
  - A story has been `In progress` past the heartbeat staleness threshold (4 h for AI agents, 7 d for humans) with no recent commits — you may take it over.
required_reading:
  - skills/_base/SKILL_ROUTER.md
  - skills/meta/update-tracker.md
  - tracker/TRACKER.md
  - AGENTS.md
applies_to: meta
owner: every agent (taking over each other's work)
last_reviewed: 2026-04-29
---

# Resume task

## Trigger

You're starting work and one of these is true:

1. A story that matches your task is **already** `In progress` (don't double-claim — resume it).
2. You were paged because a previous agent went offline mid-task.
3. The previous shift handed off a long-running story (multi-day epic).

If you skip this skill and start a fresh claim on top of an existing one, you'll fork the branch, duplicate work, and waste time.

## Required reading

1. `tracker/TRACKER.md` — find the story.
2. `skills/_base/SKILL_ROUTER.md` — confirm the route.
3. `skills/meta/update-tracker.md` — the lifecycle protocol you're inheriting.

---

## Steps

### 1. Find the abandoned story

Open `tracker/TRACKER.md`. Find a row matching your task description.

If the row's status is **`In progress`**, examine its **Notes cell**. The notes follow the canonical structured format (see §"Canonical claim format" below). You're looking for:

- Owner — who started it.
- Branch — git branch name.
- Skill — the skill being applied.
- Last step — where they paused.
- Heartbeat — last activity timestamp.

If the notes cell is **not** in the structured format, the previous agent skipped the protocol. Treat the story as orphaned (proceed to step 6 — orphan recovery).

### 2. Decide whether to resume or wait

| Situation | Action |
|-----------|--------|
| Heartbeat is **fresh** (< 4 h ago, AI agent) | Don't resume. Owner is likely still working. Pick a different story or wait. |
| Heartbeat is **stale** (> 4 h ago, AI agent; > 7 d, human) | Resume. The previous agent is gone. |
| Status is `Blocked` | Read the blocker reason. If you can unblock, do that first; then continue. |
| You were **explicitly told** to take over (handover) | Resume regardless of heartbeat. |
| Notes cell is **empty / non-structured** | Treat as orphaned — go to step 6. |

For AI agent staleness, "no commit / heartbeat in 4 h" is the canonical threshold. Adjust if the workspace policy says otherwise.

### 3. Sync the branch

```bash
git fetch --all
git checkout <branch-from-notes>
git pull --rebase origin <branch>
git log --oneline main..HEAD     # see what's already done
```

Read the commit log. Each commit should follow the convention:

- `chore(tracker): claim S0NN` — the claim commit.
- `chore(tracker): checkpoint S0NN step <N>/<M> — <short note>` — partial progress.
- Feature commits in between.

The most recent `checkpoint` commit's message tells you the last completed skill step.

### 4. Acknowledge the handover

Edit `tools/build_tracker.py`. Update the story's Notes cell to add a handover line, **without** removing the previous structured notes:

```python
# in tools/build_tracker.py, find your story
("S025", "...", "agent-bot-2",  "S0",  "EX",  ..., ..., "In progress",
 "**Resumed.**\n"
 "Branch: agent-bot/runtime-graceful-degrade\n"
 "Skill: skills/coding/implement-runtime-feature.md\n"
 "Last step (from previous agent): 5/12\n"
 "Heartbeat: 2026-04-30T16:05Z (Codex; resumed from Claude)\n"
 "Handover: previous agent paused after pre-flight budget check landed. "
 "Picking up at memory invariants step.\n"
 "Commits: abc1234 (claim), def5678 (pre-flight), 90ab12 (checkpoint 5/12)"),
```

Regenerate companions:

```bash
python tools/build_tracker.py
python tools/tracker_to_machine.py
python scripts/recalc.py tracker/IMPLEMENTATION_TRACKER.xlsx
```

Commit on the existing branch:

```bash
git add tools/build_tracker.py tracker/
git commit -m "chore(tracker): resume S025 (handover from agent-bot)"
git push
```

### 5. Read the skill from the recorded last-step onward

Open `skills/<category>/<skill-name>.md` (the path is in the Notes). Read it end-to-end **first** — even if you only need the second half — so you understand the full scope.

Then start at the next step after the recorded `Last step`. Don't redo completed work; the previous agent's commits already landed it.

If you're unsure whether a step is fully done, run the skill's Definition-of-done checks for that step's output (e.g., does the test exist? does the doc reflect the change?). If yes, move on. If no, redo.

### 6. Orphan recovery (notes cell missing or unstructured)

If you can't reconstruct state from the notes cell, you must reverse-engineer:

1. **Find the branch.** `git branch -r | grep <story-id>` or `git log --grep="S0NN" --all`.
2. **Read the commit log.** Each commit's diff tells you what was done.
3. **Apply the skill** from the start. Re-do every step's *verification* (test exists? doc updated?) and only **execute** the steps where verification fails.
4. **Rewrite the notes cell** in the canonical format (see §"Canonical claim format") so the next agent doesn't have to repeat this archaeology.
5. **Audit-log the orphan recovery** with `chore(tracker): orphan recover S0NN` so the team knows the previous claim was incomplete.

### 7. Continue from your skill

From here on, follow the matched task skill normally:

- Read its `required_reading`.
- Continue its Steps from where you stopped.
- Issue `checkpoint` commits at logical boundaries (see §"Heartbeat checkpoint convention" below).
- Close the story per `meta/update-tracker.md` AFTER phase when done.

### 8. If you also get rate-limited

You may not finish either. That's fine — the same protocol works for the *next* agent:

1. Push your latest checkpoint commit.
2. Update the Notes cell with your last step + heartbeat.
3. Push.

A third agent can pick up from there. The protocol is designed to be re-entrant.

---

## Heartbeat checkpoint convention

Long-running tasks (> 1 h) commit progress at every logical boundary so a different agent can resume without losing work. Conventions:

- After every numbered step in the skill, or every ~30 min, commit:
  ```
  chore(tracker): checkpoint S0NN step <N>/<M> — <one-line summary>
  ```
- Push after each checkpoint:
  ```bash
  git push
  ```
- Update the Notes cell **at every checkpoint** with:
  - New `Last step:`
  - New `Heartbeat: <ISO-8601> (<agent identity>)`
- Don't leave uncommitted work. If you must context-switch, commit a WIP first:
  ```
  chore(tracker): wip S0NN — branch parked at <reason>
  ```

The checkpoint commits make handover deterministic. Without them, the next agent has to read uncommitted dirty state — which they can't see.

---

## Canonical claim format (for the Notes cell)

Every `In progress` story's Notes cell follows this exact shape so resumption is mechanical:

```
**<Status word>.**             <- Active | Blocked | Resumed | Handing off
Branch: <git-branch>
Skill: skills/<category>/<name>.md
Last step: <N>/<M> (<one-line description of where you paused>)
Heartbeat: <ISO-8601 UTC> (<agent-identity>)
Open questions:
- <question 1, if any>
- <question 2>
Blockers:
- <blocker 1, with link to issue or ADR if applicable>
Commits:
- <hash> <commit message>
- <hash> <commit message>
```

If a field is empty, write `Open questions: none`. Don't leave fields out — that's what triggers orphan recovery for the next agent.

---

## Definition of done (for resume)

- [ ] Existing `In progress` story identified before any new claim.
- [ ] Branch checked out, pulled, history reviewed.
- [ ] Notes cell updated with `**Resumed.**` block + new heartbeat.
- [ ] Commit `chore(tracker): resume S0NN (handover from <prev>)` pushed.
- [ ] Skill's last-step verified before continuing (no rework if it landed; redo if it didn't).
- [ ] Tracker companions regenerated (xlsx + md + json + csv).

## Anti-patterns

- ❌ Claiming a fresh story when one already exists `In progress` for the same task. Forking the work guarantees a merge conflict and wasted hours.
- ❌ Resuming with a fresh heartbeat (< 4 h) without explicit handover.
- ❌ Force-pushing over commits you didn't author. Always rebase or merge cleanly.
- ❌ Skipping the `chore(tracker): resume` audit commit.
- ❌ Re-doing work that already landed. Read the diffs first.
- ❌ Leaving the Notes cell stale after taking over. The next agent will assume *you* are still active.
- ❌ Inventing a new branch name. Always reuse the existing one (Owner of the original work is preserved by git).

## Related skills

- `meta/update-tracker.md` — the lifecycle this resumes into.
- `meta/write-pr.md` — when you eventually open the PR, all the original commits stay intact.

## References

- `tracker/TRACKER.md` — current state.
- `engineering/HANDBOOK.md` §3 — branching conventions.
