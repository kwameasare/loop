---
name: parallel-work
description: |
  Use whenever multiple coding agents are working on this repo at the same
  time. Mandatory when you (the agent) are about to claim a story and one or
  more other agents are also active. Covers: how to pick a story safely
  without colliding, how to handle claim races, how to coordinate edits to
  hot shared files (SCHEMA.md, build_tracker.py, ENV_REFERENCE.md, etc.),
  how to recover when your PR conflicts with someone else's, and the hard
  caps on how much state any one agent may hold.
when_to_use: |
  BEFORE you claim a story whenever (a) the tracker shows ≥1 story in
  status "In progress", "Handing off", or "Blocked" with a non-stale
  heartbeat, OR (b) you were spawned by an orchestrator that told you
  other agents are running. ALSO when you finish a story and a successor
  agent will pick the next one — drop a final heartbeat and confirm your
  branch is pushed.
required_reading:
  - loop_implementation/skills/meta/update-tracker.md
  - loop_implementation/skills/meta/resume-task.md
  - loop_implementation/skills/_base/SKILL_ROUTER.md
applies_to: meta
owner: every agent
last_reviewed: 2026-04-30
---

# Parallel work — multi-agent coordination

## Trigger

This skill applies the moment more than one autonomous agent is making
commits to this repo on overlapping windows. The single-agent protocol
(`update-tracker.md` + `resume-task.md`) still holds; this skill adds the
coordination rules that make N agents not stomp each other.

## Why a separate skill

The tracker is the only synchronizer; agents do not communicate
in-band. The repository's git history *is* the message bus. That works
only if every agent obeys the same five rules below.

---

## The five hard rules

### Rule 1 — One story claim per agent at a time

You claim one story, ship it, mark it `Done`, push, then claim the next.
Never hold two open claims. If your work expands and you discover a
sub-task that should be its own story, **add it to the backlog** (edit
`tools/_stories_v2.py`) and link it from your current story's notes — do
not silently widen the scope of the claim you're holding.

### Rule 2 — Pick atomically via `tools/pick_next_story.py`

Before claiming, run:

```bash
python tools/pick_next_story.py --owner <your-identity> --json
```

The picker:

* filters out stories that are already claimed,
* filters out stories whose `[extends Sxxx]` deps are not yet `Done`,
* filters out closed-sprint stories (S0, S1),
* prefers low-priority numeric, low sprint-id, low story-id,
* (with `--avoid-hot-files`) penalizes stories that look like they'll
  touch the same shared files as currently-claimed work.

Then claim the printed id. **The picker does not reserve the story** —
only the merge of your claim PR does. See Rule 3.

### Rule 3 — Claim is a single small PR; on conflict, the loser re-picks

Your claim is a separate PR titled `chore(tracker): claim S<NNN>` whose
only diff is the StoryV2 entry update in `tools/_stories_v2.py`
(setting `status="In progress"`, `owner=<you>`, structured `notes` per
`update-tracker.md`) plus the regenerated tracker outputs.

Two agents may claim the same story at the same instant. Whichever PR
merges first wins. The losing agent will see a merge conflict on
`tools/_stories_v2.py` for that story's line. **The losing agent must
abandon that PR and re-run the picker** — do not force-merge over the
winner.

> Pseudocode for the claim flow:
>
> ```bash
> chosen=$(python tools/pick_next_story.py --owner $ID)
> git checkout -b $ID/${chosen,,}-claim
> # edit _stories_v2.py for $chosen → status=In progress, owner=$ID, notes=...
> python tools/build_tracker.py
> python tools/check_tracker_notes.py
> git commit -am "chore(tracker): claim $chosen"
> gh pr create --title "chore(tracker): claim $chosen" --body "..."
> # loop until merged OR loser:
> gh pr merge --auto --squash || { echo "claim lost"; exit 1; }
> ```

### Rule 4 — Hot files are sequenced via merge order, not via locks

There is no global lock. The `docs-with-code` and
`checkpoint-discipline` gates plus the per-PR rebase make hot-file
edits manageable as long as **each PR touches the minimum slice**.
Concretely:

* **Edit only the section relevant to your story** in `SCHEMA.md`,
  `ENV_REFERENCE.md`, `ERROR_CODES.md`. Tag the edited block with the
  story id (e.g. `<!-- S104 -->`) so successors see who touched what.
* **Append-only by convention** — do not reorder existing rows in
  reference tables; only add new rows below or in alphabetic position.
  This makes 3-way merges trivial.
* **Tracker source edits go in `tools/_stories_v2.py` line-per-story.**
  Each StoryV2 is exactly one line, so two agents claiming different
  stories produce non-overlapping diffs that auto-merge.
* **Never** rewrite history (`git push --force`) on a branch another
  agent might be reading. Use `git rebase main` + `git push` only.

When your PR fails the rebase against `main` because someone else's
hot-file edit landed first, **never** `-X theirs` or `-X ours` blindly:
read both diffs, hand-merge, re-run the lints, re-push.

### Rule 5 — Heartbeats are the only liveness signal

Every checkpoint commit MUST update the `Heartbeat:` field in your
story's notes with the current UTC ISO timestamp and your agent
identity. The orchestrator (or `meta/resume-task.md`) treats a stale
heartbeat as evidence to take over.

* AI agents: heartbeat at most **30 minutes apart** (not 4 h — that
  threshold is for handoff to a fresh agent; the inter-checkpoint cap
  is much tighter).
* If you pause for any reason (rate limit, tool failure), commit a WIP
  with a fresh heartbeat first. **No silent pauses.**
* On `Done`, your final heartbeat is the close commit's UTC timestamp.

---

## Forbidden patterns

These are explicit anti-patterns that defeat the multi-agent protocol.
Any of them is a CRITICAL incident:

| Anti-pattern | Why it breaks coordination |
|---|---|
| Stub-shipping any story (closing the StoryV2 with status=Done while the AC is not independently met by exercised code) | This is the actual failure mode the historical bulk-passes encoded. The `audit_agent_behaviour.py` substance check + the AC-based gate in `close` will surface it; reopen and finish. Combining stories is fine — closing them empty is not. |
| `pass<N> close <K> stories`-style commit titles (or `close <K> stories`) | Batch-grind tell. Multiple bite-sized stories MAY share a commit when the work is genuinely combinable — but title the commit by what was built (`feat(security): PASETO encode + decode (S105, S106)`), not by the count. Enforced by `tools/check_no_bulk_close.py`. |
| Closing ≥4 stories in a single commit | At that scale the "natural unit" framing is implausible. Either the four were really one story (merge them in `_stories_v2.py`) or you're stub-shipping (split into smaller commits). |
| Direct commits to `main` | Bypasses `checkpoint-discipline`, `tracker-clean`, and `docs-with-code` gates which are PR-only. **Branch protection MUST be applied** (see `docs/branch-protection.md`) before parallel work begins. |
| Holding multiple open claims at once | Two stories' diffs entangled in one branch → can't ship one without the other → blocks two slots in the tracker. |
| Force-pushing over another agent's work on a shared branch | Loses commits silently; defeats the rebase model. |
| Claiming a story whose `[extends Sxxx]` dep is `Not started` | The dep's API/types/migration aren't there yet; you'll either re-do them or block waiting. The picker filters this out — don't manually override. |
| Skipping `pick_next_story.py` and "just picking S104 because it sounds easy" | The hot-file-conflict heuristic exists to spread agents across the codebase; bypassing it concentrates contention. |

---

## Definition of done (for this skill itself)

You're following the parallel-work protocol if and only if:

- [ ] Every claim was selected via `pick_next_story.py`
- [ ] Every claim was a separate small PR, merged before any feature commit
- [ ] On conflict, you abandoned and re-picked rather than force-merging
- [ ] Every checkpoint updated the `Heartbeat:` field with a fresh UTC stamp
- [ ] You hold at most one open claim at any time
- [ ] All your edits to hot files were minimal, tagged with story id, and
      append-only where convention applies
- [ ] You never stub-shipped a story (every closed AC was exercised by code)
- [ ] You never used `pass<N> close <K> stories`-style commit titles or closed ≥4 stories in one commit
- [ ] You never committed direct to `main`

If any of these is `[ ]`, stop, fix, file an incident note in your
story's `Open questions:`.

---

## Operator notes (for the human running multiple agents)

### Working-directory isolation (mandatory for local agents)

If two locally-running agents share one checked-out working tree, one
agent's `git checkout` clobbers the other's WIP. **Don't.** Each agent
self-creates a git worktree via the lifecycle tool — operator does
nothing:

```bash
# Inside each agent's session:
export LOOP_AGENT_ID=<owner>            # claude-a, copilot-b, codex-c, …
python tools/agent_lifecycle.py init    # creates ../bot-<owner>/
cd ../bot-<owner>                        # subsequent commands run here
python tools/agent_lifecycle.py pick    # rest of the lifecycle is the
python tools/agent_lifecycle.py claim … # tool, not bespoke git/gh
python tools/agent_lifecycle.py checkpoint …
python tools/agent_lifecycle.py close …
# end of session:
python tools/agent_lifecycle.py teardown
```

The underlying primitives (`scripts/spawn_agent_worktree.sh` and
`scripts/cleanup_agent_worktree.sh`) are still available for operator
debugging, but the lifecycle tool is what agents are expected to call.

Properties of this setup:

* Every agent has its own working directory; `git checkout` in one is
  invisible to the others.
* All worktrees share the same `.git` store, so branches and refs sync
  via `git fetch` / `git push` once — no need to re-clone.
* The same branch can never be checked out in two worktrees
  simultaneously — git refuses. That's the safety: if two agents try to
  claim the same story they'll collide at worktree-creation time, not
  silently corrupt each other's work mid-story.
* Disk cost: low. Worktrees share git objects; only the working-tree
  files are duplicated.

**Cloud-hosted agents (GitHub Copilot Coding Agent) don't need this.**
Each Copilot task spins up its own ephemeral sandbox with a fresh clone;
the worktree pattern is for **local IDE/CLI agents** running on the
operator's workstation simultaneously.

### Other operator rules

* **Cap parallelism at five.** Beyond that the merge-conflict tax
  outweighs throughput. Adjust by editing
  `loop_implementation/operations/MAX_PARALLEL_AGENTS` (a single-int
  text file the orchestrator reads).
* **Prefer cross-epic spread.** Five agents on E10 (Studio) will fight
  over the studio package; five agents spread across E2/E3/E5/E6/E10
  rarely overlap.
* **Branch-protection prerequisite.** If branch protection isn't
  applied on GitHub yet, multi-agent work will silently bypass every
  CI gate. See `docs/branch-protection.md` and bootstrap story
  `S099 — Apply branch protection on GitHub`.
* **Audit cadence.** Once a week, run
  `python tools/audit_agent_behaviour.py --since 7.days` (added in S099)
  to confirm every closed story had a claim PR + checkpoint commits +
  closed PR, and that no commits hit `main` directly.
