---
name: rollback-deploy
description: Use when reverting a bad deploy.
when_to_use: |
  - Eval regression slipped past gating.
  - Customer-visible failure post-deploy.
  - Performance budget regressed.
required_reading:
  - engineering/RUNBOOKS.md   # RB-018 mass deploy rollback
  - architecture/ARCHITECTURE.md   # §4.3 deploy flow
applies_to: ops
owner: Founding Eng #2 (Infra) + Sec eng for audit
last_reviewed: 2026-04-29
---

# Rollback deploy

## Trigger

Bad deploy, customer pain, eval regression escaped to prod.

## Required reading

`engineering/RUNBOOKS.md` RB-018.

## Steps

Follow RB-018 verbatim. Summary:

1. Identify the offending agent version + rollout %.
2. `loop admin deploy rollback --agent=<id> --target=<previous-version>`.
3. Verify all pods serve rollback version.
4. Disable eval-gating override until root cause is fixed.
5. PIR within 24 h.
6. Add the missing eval case before re-deploying.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Rollback applied.
- [ ] All pods on previous version (`kubectl rollout status` clear).
- [ ] Eval-gating override disabled.
- [ ] PIR ticket open.
- [ ] Missing eval case added before re-deploy.

## Anti-patterns

- ❌ Re-deploying the same broken version "with a different config."
- ❌ Skipping the PIR.
- ❌ Permanent eval-gating override.

## Related skills

- `ops/triage-incident.md`, `testing/write-eval-suite.md`.

## References

- `engineering/RUNBOOKS.md` RB-018.
