<!--
Reminder: title MUST be a Conventional Commit (feat/fix/docs/refactor/chore/...).
Add `!` for breaking changes (e.g. `feat(sdk)!: ...`). See
loop_implementation/skills/meta/write-pr.md for the full protocol.
-->

## What & why

<!-- One paragraph: why this change exists. The diff shows what. -->

## Changes

- <!-- Bullet list of touched files/areas, not every line. -->

## Testing

<!--
What was added; how to reproduce verification (commands, fixtures, screenshots).
Runtime PRs: include eval-harness numbers. UI PRs: include screenshots.
-->

## Story

Closes S0NN
<!-- Replace with the actual story ID. Tracker: loop_implementation/tracker/TRACKER.md -->

## Migration / breaking change

<!-- Call out anything that requires a migration, env var change, or config update. Otherwise: "None." -->

---

## Pre-merge checklist (`skills/meta/write-pr.md`)

- [ ] Tracker `claim S0NN` (or `resume S0NN`) commit is the **first** commit on this branch.
- [ ] Checkpoint commits exist for any task that took > 1h (`chore(tracker): checkpoint S0NN step <N>/<M>`).
- [ ] Tracker `close S0NN` commit is the **last** commit on this branch.
- [ ] Notes cell on the closing tracker entry uses the canonical structured format (skills/meta/update-tracker.md).
- [ ] Tests pass (unit + integration).
- [ ] Lint + typecheck clean.
- [ ] No cloud-SDK import in forbidden packages (see CLOUD_PORTABILITY.md).
- [ ] Story ID referenced above (`Closes S0NN`).
- [ ] Docs updated in this PR (no separate doc-only follow-up).
- [ ] No secrets in diff (pre-commit `detect-secrets` passed).
- [ ] Eval suite passed (runtime PRs).
- [ ] Bench non-regressed (hot-path PRs).
- [ ] Right reviewers tagged via CODEOWNERS (cross-cutting → every affected owner).
