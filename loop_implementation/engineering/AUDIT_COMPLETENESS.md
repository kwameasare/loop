# Loop — Audit Trail Completeness Matrix

**Status:** v0.1  •  **Owners:** Sec eng (audit log).
**Verification:** Automated pytest + manual audit-code walkthrough.
**SOC2 evidence:** CC6.5 (data access), CC7.3 (logging).

This document is the canonical matrix of all Loop write endpoints → audit-event coverage. Every write endpoint must emit an audit event; this document tracks coverage and identifies gaps that must be remediated.

---

## 1. Coverage matrix

| Endpoint | Method | Scope(s) | Audit event type | Handler responsible | Coverage | Follow-up issue |
| --- | --- | --- | --- | --- | --- | --- |
| `/v1/workspaces` | POST | workspace:create | workspace.created | cp-api POST /workspaces | ✅ | — |
| `/v1/workspaces/{id}` | PATCH | workspace:write | workspace.updated | cp-api PATCH /workspaces/{id} | ✅ | — |
| `/v1/workspaces/{id}` | DELETE | workspace:write | workspace.deleted | cp-api DELETE /workspaces/{id} | ✅ | — |
| `/v1/workspaces/{id}/members` | POST | workspace:write | member.invited | cp-api POST /workspaces/{id}/members | ✅ | — |
| `/v1/workspaces/{id}/members/{user_id}` | PATCH | workspace:write | member.role_changed | cp-api PATCH /workspaces/{id}/members/{user_id} | ✅ | — |
| `/v1/workspaces/{id}/members/{user_id}` | DELETE | workspace:write | member.removed | cp-api DELETE /workspaces/{id}/members/{user_id} | ✅ | — |
| `/v1/workspaces/{id}/api-keys` | POST | workspace:write | api_key.created | cp-api POST /workspaces/{id}/api-keys | ✅ | — |
| `/v1/workspaces/{id}/api-keys/{key_id}` | DELETE | workspace:write | api_key.revoked | cp-api DELETE /workspaces/{id}/api-keys/{key_id} | ✅ | — |
| `/v1/workspaces/{id}/secrets` | POST | workspace:write | secret.created | cp-api POST /workspaces/{id}/secrets | ✅ | — |
| `/v1/workspaces/{id}/secrets/{secret_id}` | PATCH | workspace:write | secret.rotated | cp-api PATCH /workspaces/{id}/secrets/{secret_id} | ✅ | — |
| `/v1/workspaces/{id}/secrets/{secret_id}` | DELETE | workspace:write | secret.deleted | cp-api DELETE /workspaces/{id}/secrets/{secret_id} | ✅ | — |
| `/v1/agents` | POST | agent:write | agent.created | cp-api POST /agents | ✅ | — |
| `/v1/agents/{id}` | PATCH | agent:write | agent.updated | cp-api PATCH /agents/{id} | ✅ | — |
| `/v1/agents/{id}` | DELETE | agent:write | agent.deleted (soft-delete, archived) | cp-api DELETE /agents/{id} | ✅ | — |
| `/v1/agents/{id}/deploy` | POST | agent:write | agent.deployed | dp-runtime POST /agents/{id}/deploy | ✅ | — |
| `/v1/agents/{id}/promote` | POST | agent:write | agent.promoted | dp-runtime POST /agents/{id}/promote | ✅ | — |
| `/v1/agents/{id}/rollback` | POST | agent:write | agent.rolled_back | dp-runtime POST /agents/{id}/rollback | ✅ | — |
| `/v1/agents/{id}/eval-gating-override` | POST | agent:write | eval_gating.override_requested | dp-runtime POST /agents/{id}/eval-gating-override | ✅ | — |
| `/v1/conversations` | POST | agent:write | turn.started (implicit agent write) | dp-runtime POST /conversations | ⚠️ | S582 — map turn.started to conversation.initiated |
| `/v1/conversations/{id}/messages` | POST | agent:write | turn.updated | dp-runtime POST /conversations/{id}/messages | ✅ | — |
| `/v1/conversations/{id}/takeover` | POST | human:write | conversation.takeover_started (HITL) | cp-api POST /conversations/{id}/takeover | ✅ | — |
| `/v1/knowledge/documents` | POST | knowledge:write | knowledge.document_ingested | kb-engine POST /knowledge/documents | ✅ | — |
| `/v1/knowledge/documents/{id}` | DELETE | knowledge:write | knowledge.document_removed | kb-engine DELETE /knowledge/documents/{id} | ✅ | — |
| `/v1/evals/suites` | POST | eval:write | eval.suite_created | dp-runtime POST /evals/suites | ⚠️ | S583 — missing audit event for suite creation |
| `/v1/evals/suites/{id}` | PATCH | eval:write | eval.suite_updated | dp-runtime PATCH /evals/suites/{id} | ⚠️ | S583 |
| `/v1/evals/test-cases` | POST | eval:write | eval.test_case_created | dp-runtime POST /evals/test-cases | ✅ | — |
| `/v1/evals/test-cases/{id}` | DELETE | eval:write | eval.test_case_deleted | dp-runtime DELETE /evals/test-cases/{id} | ✅ | — |
| `/v1/evals/runs` | POST | eval:write | eval.run_started | dp-runtime POST /evals/runs | ✅ | — |
| `/v1/workspaces/{id}/settings` | PATCH | workspace:write | workspace.settings_updated | cp-api PATCH /workspaces/{id}/settings | ⚠️ | S584 — missing coverage for custom_pii_patterns, budget_alert_threshold |
| `/v1/webhooks` | POST | webhook:write | webhook.created | cp-api POST /webhooks | ⚠️ | S585 — webhook lifecycle audit events missing |
| `/v1/webhooks/{id}` | DELETE | webhook:write | webhook.deleted | cp-api DELETE /webhooks/{id} | ⚠️ | S585 |
| `/v1/workspaces/{id}/end-users/{user_id}` | DELETE | workspace:write (GDPR erasure) | end_user.erased | cp-api DELETE /workspaces/{id}/end-users/{user_id} | ✅ | — |

---

## 2. Gap analysis

### 2.1 Critical gaps (P1 — must fix before SOC2 audit)

**None identified.** All core resource lifecycle endpoints (create/update/delete for workspaces, agents, API keys, secrets, knowledge, evals) are covered.

### 2.2 High-priority gaps (P2 — remediate by end of Q2)

| Gap | Endpoint | Issue | Fix |
| --- | --- | --- | --- |
| G1 | `/v1/evals/suites` POST/PATCH | Audit events `eval.suite_created` and `eval.suite_updated` are referenced in this matrix but not currently emitted. | Add audit emitters to dp-runtime's eval suite handlers. Ticket: S583. |
| G2 | `/v1/workspaces/{id}/settings` PATCH | Selective audit logging — the PATCH handler logs generic "settings_updated" but does not record which settings changed (e.g., budget_alert_threshold, custom_pii_patterns). Needed for compliance with CC6.5 (data access control changes). | Emit scoped audit events: `workspace.budget_limit_changed {old: X, new: Y}`, `workspace.pii_patterns_updated {patterns_count}`. Ticket: S584. |
| G3 | `/v1/webhooks` POST/DELETE | Webhook lifecycle audit events are not emitted. Webhooks are an out-of-process notification mechanism; changes should be audited. | Add audit emitters to cp-api webhook handlers. Ticket: S585. |

### 2.3 Low-priority gaps (P3 — nice-to-have, monitor)

| Gap | Endpoint | Issue | Fix |
| --- | --- | --- | --- |
| G4 | `/v1/conversations` POST (turn initiation) | Turning is user-driven (agent-to-customer); the audit event `turn.started` is emitted at the dataplane. Linking this to the user/API-key that initiated the turn (customer-facing agent call) requires propagating auth context through SSE streaming. Currently audit log shows "dataplane service" as actor, not the customer's API key. | Add request-scoped actor context propagation to streaming handlers. Ticket: S586 (lower priority, requires refactor). |
| G5 | Batch operations | Future: if bulk delete / bulk update endpoints are added, ensure each affected resource emits its own audit event (or bulk event with count + representative sample). | Monitor for new batch endpoints. |

---

## 3. Audit event schema

Every audit event must contain:

```json
{
  "event_type": "string",
  "actor": {
    "id": "string (API key prefix or user ID)",
    "type": "api_key | user | service_account",
    "workspace_id": "string"
  },
  "resource": {
    "type": "string (workspace | agent | api_key | secret | knowledge_document | eval_suite | webhook | end_user)",
    "id": "string"
  },
  "action": "create | update | delete | deploy | promote | rollback | invite | role_change | remove | override | ingest | takeover | rotate | erase",
  "timestamp": "RFC3339",
  "request_id": "string (correlation ID)",
  "ip_address": "string",
  "user_agent": "string",
  "status": "success | authorization_denied | validation_failed",
  "details": {
    "before": { "key": "value" } | null,
    "after": { "key": "value" } | null,
    "reason": "string (if action=delete, reason for soft-delete e.g. 'archived')"
  },
  "prev_entry_hash": "sha256(previous_audit_entry)",
  "entry_hash": "sha256(this_entry)"
}
```

---

## 4. Remediation tracking

Follow-up issues filed in the tracker:

- **S582** — map turn.started to conversation.initiated audit event (actor context propagation)
- **S583** — add audit events for eval suite creation/update
- **S584** — add scoped audit events for workspace settings changes (budget, PII patterns)
- **S585** — add audit events for webhook lifecycle (create, delete)
- **S586** — propagate actor context through SSE streaming (lower priority)

---

## 5. Verification

### 5.1 Automated

Run after every endpoint change:

```bash
# Validate that every handler in the codebase that performs a write
# either emits an audit event or is exempted with a comment:
# "AUDIT: <reason>" (e.g., "AUDIT: read-only operation despite POST")
python tools/check_audit_completeness.py
```

The checker scans all handlers for write operations (database `.create()`, `.update()`, `.delete()`), cross-references the endpoint in this matrix, and fails if the audit event is not found.

### 5.2 Manual

Quarterly audit walkthrough (paired engineer + sec eng):
1. Pick a random endpoint from §1.
2. Trace the code from handler → database write → audit log emitter.
3. Reproduce locally; verify audit log entry appears in ClickHouse within 5 sec.
4. Verify the entry includes actor, timestamp, resource ID, before/after diffs (where applicable).

---

## 6. Compliance mapping

| Standard | Control | Evidence |
| --- | --- | --- |
| SOC2 CC6.5 | Data access and changes are logged | This matrix + audit log in ClickHouse |
| SOC2 CC7.3 | Logging and monitoring (events are auditable) | Audit event schema (§3) + retention policy (SECURITY.md §7.1) |
| GDPR Art. 5(1)(f) | Accountability; records of processing | Audit log subject to right-of-access |
| ISO 27001 A.12.4.1 | Recording of user activities | This matrix + audit trail integrity checks |

---

## 7. Known deviations

These endpoints are intentionally not audit-logged (with reasoning):

- `GET *` — read operations don't trigger audit events (out-of-scope per CC6.5 focus on data *changes*); however, `audit:read` scope controls access to the audit log itself.
- `/healthz`, `/metrics` — operational endpoints.
- Internal service-to-service calls (e.g., dp-runtime → cp-api for backup coordination) — logged in application logs, not audit trail; traced via `request_id`.

---

## Appendix A: Gap remediation PRs

_(Linked upon completion of S582–S586.)_
