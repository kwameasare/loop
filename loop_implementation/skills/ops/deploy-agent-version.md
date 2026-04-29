---
name: deploy-agent-version
description: Use when promoting an agent version through canary → prod, or rolling out an updated runtime/gateway/channel image.
when_to_use: |
  - `loop deploy` from a builder.
  - Manual promotion via `loop admin deploy promote`.
  - Cutting a release of any service image.
required_reading:
  - architecture/ARCHITECTURE.md   # §4.3 eval-gated deploy
  - engineering/HANDBOOK.md         # §8 operations cadence
  - engineering/RUNBOOKS.md         # RB-018 mass rollback
  - adrs/README.md                  # ADR-009 (agent versioning), ADR-015 (eval-gating)
applies_to: ops
owner: Founding Eng #2 (Infra)
last_reviewed: 2026-04-29
---

# Deploy agent version

## Trigger

Promoting an agent version through canary → prod, or shipping a service image.

## Required reading

ADR-009, ADR-015; RB-018.

## Steps

1. **Pre-flight:**
   - All required CI checks green.
   - Eval suite passed (no regression > 5%, configurable per workspace).
   - Cassettes ≤ 30 days old.
   - Bench shows no perf regression.
2. **Canary first** (always):
   - `loop deploy --canary 10` deploys at 10% traffic.
   - Soak ≥ 30 min for low-traffic workspaces, ≥ 2 h for high-traffic.
   - Monitor: error rate, p99 latency, cost per turn, eval-replay scores.
3. **Promote** when canary is green:
   - `loop deploy promote --version <N>`. Atomic flip.
   - Channel rollout: 10% → 50% → 100% over a configured window (default 1 h).
4. **Rollback** path always ready:
   - `loop deploy rollback --version <N-1>`. Apply RB-018.
   - Eval-gating override after rollback should be temporary; root cause fix before re-deploy.
5. **Audit-log entries:** `agent.deploy.canary_start`, `agent.deploy.promoted`, `agent.deploy.rolled_back`. Apply `security/add-audit-event.md`.
6. **Notifications:**
   - Slack `#deploys` for every deploy.
   - Customer-success notified for any prod rollback affecting Enterprise customers.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Eval gate passed (or override justified + audit-logged).
- [ ] Canary stage with soak window.
- [ ] Monitoring confirmed green before full promotion.
- [ ] Rollback playbook ready (RB-018).
- [ ] Audit log entries emitted.
- [ ] Slack `#deploys` updated.

## Anti-patterns

- ❌ Skipping canary.
- ❌ Promoting on red eval scores.
- ❌ Ad-hoc rollback without eval-gating override audit.
- ❌ Long soak skipped because "it's a minor change."

## Related skills

- `ops/rollback-deploy.md`, `security/add-audit-event.md`.

## References

- ADR-009, ADR-015.
- `engineering/RUNBOOKS.md` RB-018.
