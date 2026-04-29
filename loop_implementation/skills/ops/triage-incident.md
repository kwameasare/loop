---
name: triage-incident
description: Use when paged for SEV1 or SEV2.
when_to_use: |
  - PagerDuty alert fires.
  - Customer reports degraded service.
  - Internal alert (eval drift, error rate spike).
required_reading:
  - engineering/RUNBOOKS.md     # all RBs
  - engineering/SECURITY.md     # §10 incident response
applies_to: ops
owner: primary on-call
last_reviewed: 2026-04-29
---

# Triage incident

## Trigger

You are paged.

## Required reading

`engineering/SECURITY.md` §10; the relevant runbook from `engineering/RUNBOOKS.md`.

## Steps

1. **Acknowledge within SLA** (SEV1 ≤ 5 min, SEV2 ≤ 15 min, SEV3 ≤ 1 h).
2. **Open `#inc-YYYYMMDD-<short-slug>`** and post the alert text.
3. **Assign roles:** incident commander (primary on-call by default), comms lead (CEO for SEV1), scribe, tech lead.
4. **Match to runbook.** If the alert maps to RB-NNN, follow it.
5. **Status page** within 15 min for SEV1, 30 min for SEV2.
6. **Customer comms** within 1 h for SEV1.
7. **Mitigate first, fix second.** Roll back if available; degrade gracefully if possible.
8. **Verify recovery** with the same metrics that triggered the alert.
9. **Post-incident review** within 48 h. Blameless. Action items in Linear, owned + dated.
10. **Update runbook** if the incident exposed gaps. Apply `observability/add-runbook.md`.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Acked within SLA.
- [ ] Incident channel open.
- [ ] Roles assigned.
- [ ] Status page updated.
- [ ] Customer comms (SEV1).
- [ ] Mitigation deployed.
- [ ] Recovery verified.
- [ ] PIR within 48 h.
- [ ] Runbook updated.

## Anti-patterns

- ❌ Acking and waiting for "the right person."
- ❌ Mitigating with no comms.
- ❌ Skipping the PIR because "we know what happened."
- ❌ Blame in the PIR.

## Related skills

- Whichever RB-NNN matches the symptom.
- `observability/add-runbook.md`.

## References

- `engineering/SECURITY.md` §10.
- `engineering/RUNBOOKS.md`.
