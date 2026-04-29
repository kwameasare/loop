---
name: add-audit-event
description: Use when adding an admin action that should appear in the immutable audit log.
when_to_use: |
  - Workspace lifecycle (create, delete, plan change).
  - Member invite / role change / removal.
  - API key create / revoke.
  - Secret create / rotate / access (sample reads, not bulk).
  - Agent deploy / promote / rollback.
  - Eval gating override.
  - Budget changes.
  - HITL takeover.
  - Data export.
required_reading:
  - engineering/SECURITY.md   # §7.1 audit log
  - data/SCHEMA.md             # audit_log table
  - adrs/README.md             # ADR-022 (idempotency for audit)
applies_to: security
owner: Sec/Compliance Eng
last_reviewed: 2026-04-29
---

# Add audit event

## Trigger

You're implementing an action that, if a customer auditor asked "who did this and when?", we'd need to answer.

## Required reading

`engineering/SECURITY.md` §7.1.

## Steps

1. **Append to the audit log via `audit_log_append(event)`** — never write directly to the table.
2. **Required fields:**
   - `actor` (user_id or api_key_id).
   - `action` (canonical verb-noun: `agent.deploy`, `member.invite`, `secret.rotate`, …).
   - `target` (workspace_id, agent_id, etc.).
   - `timestamp` (server-side, immutable).
   - `ip` + `user_agent`.
   - `request_id` + `trace_id`.
   - `before` / `after` JSON snapshot for state changes.
3. **Cryptographic chain:** the helper computes `prev_hash` automatically. Don't bypass.
4. **Action vocabulary:** reuse existing verbs (see §7.1 table). New verbs: PR them in.
5. **Idempotency:** if the same logical action is triggered twice with the same `Idempotency-Key`, audit log gets one entry, not two.
6. **Sensitive data:** never log secret values; log secret refs. Never log full PII; log hashes if needed for correlation.
7. **Test:**
   - Unit: action emits exactly one audit row.
   - Integration: chain verification passes after the action.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] All required fields populated.
- [ ] `audit_log_append` used (not raw INSERT).
- [ ] No secret values or full PII in `before`/`after`.
- [ ] Action verb consistent with the table.
- [ ] Test for emission + chain integrity.

## Anti-patterns

- ❌ Writing directly to the audit_log table.
- ❌ Logging secret values.
- ❌ Custom verbs that don't follow `<resource>.<action>`.
- ❌ Skipping audit on a privileged action because "it's just a config change."

## Related skills

- `security/update-threat-model.md`, `engineering/RUNBOOKS.md` RB-014 (chain integrity check).

## References

- `engineering/SECURITY.md` §7.1.
- `data/SCHEMA.md` audit_log.
