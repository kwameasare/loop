---
name: add-runbook
description: Use when codifying response to a recurring failure. Add a new RB-NNN to engineering/RUNBOOKS.md.
when_to_use: |
  - Same incident class fired twice in a quarter.
  - New service with novel failure modes.
  - DR scenario coverage gap.
required_reading:
  - engineering/RUNBOOKS.md
  - engineering/templates/RUNBOOK_TEMPLATE.md
  - engineering/SECURITY.md   # §10 incident response
applies_to: observability
owner: on-call rotation
last_reviewed: 2026-04-29
---

# Add runbook

## Trigger

Recurring failure or DR gap.

## Required reading

`engineering/RUNBOOKS.md` index + the template at `engineering/templates/RUNBOOK_TEMPLATE.md`.

## Steps

1. **Pick the next free `RB-NNN`** in the §0 index. Never reuse retired numbers.
2. **Copy the template** into the file.
3. **Symptoms section:** the literal alert names, log lines, dashboard panels someone copy-pastes into search at 3 a.m.
4. **Steps:** numbered, copy-pasteable. Assume runner has shell access but no recent context. Include exact CLI commands.
5. **Rollback:** if any step makes things worse, how to undo it.
6. **Anti-patterns:** stuff people have actually done that made it worse.
7. **Drill it once before first prod use.** Capture the drill date in §0 index.
8. **Re-drill at least every 6 months.**

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] `RB-NNN` row added to §0 index.
- [ ] Template fully filled (no TODOs).
- [ ] Owner + SEV target set.
- [ ] First drill scheduled (or done) — date in §0.
- [ ] Symptoms have literal log/alert text.
- [ ] Steps are copy-pasteable.

## Anti-patterns

- ❌ Steps that say "investigate" without saying how.
- ❌ Symptoms that don't match what alerts actually say.
- ❌ Skipping the drill.

## Related skills

- `ops/triage-incident.md`, `ops/dr-drill.md`.

## References

- `engineering/RUNBOOKS.md`.
- `engineering/templates/RUNBOOK_TEMPLATE.md`.
