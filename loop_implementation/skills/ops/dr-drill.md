---
name: dr-drill
description: Use when running a scheduled DR drill.
when_to_use: |
  - Weekly chaos day (random pod kill).
  - Monthly Postgres failover.
  - Quarterly region failover.
  - Twice-yearly cross-cloud DR.
  - Quarterly Vault unseal + audit chain check.
required_reading:
  - engineering/DR.md       # §4 drill cadence
  - engineering/RUNBOOKS.md  # the RB matching the drill
applies_to: ops
owner: Founding Eng #2 + Sec eng
last_reviewed: 2026-04-29
---

# DR drill

## Trigger

Scheduled drill on the cadence in `engineering/DR.md` §4.

## Required reading

`engineering/DR.md`; the runbook for the drill scenario.

## Steps

1. **Schedule** in advance (calendar block; team aware).
2. **Set up:** dry-run environment if possible; production drills only when team is ready.
3. **Trigger the failure** per the runbook.
4. **Measure:** RTO (start of failure → end of recovery), RPO (data loss in seconds), team response time.
5. **Pass criteria:** see `engineering/DR.md` §4 table.
6. **Capture results** in the runbook's "Recent drills" section.
7. **Action items** for any gap. PIR within 48 h.
8. **Communicate** results in the engineering channel.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Scheduled + announced.
- [ ] Failure injected per runbook.
- [ ] RTO/RPO measured.
- [ ] Pass/fail recorded in runbook.
- [ ] Action items in Linear.

## Anti-patterns

- ❌ Skipping a drill because "things are calm."
- ❌ Drills without measurement.
- ❌ Treating a failed drill as a non-event.

## Related skills

- `observability/add-runbook.md`.

## References

- `engineering/DR.md` §4.
- `engineering/RUNBOOKS.md`.
