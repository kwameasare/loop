# Loop — Support Ticketing Runbook & Routing Rules (Front)

**Status:** v1.0  •  **Owner:** Support engineering  •  **Last updated:** 2025-01

This document describes how support tickets are created, routed, and escalated using [Front](https://front.app) as the ticketing integration layer. It supplements the operational runbooks in `RUNBOOKS.md`.

---

## 1. Inbound channels → Front inbox

All customer-facing channels are forwarded to Front and land in the **Loop Support** team inbox.

| Channel | Address / hook | Front inbox |
|---------|---------------|-------------|
| Primary support email | support@loop.ai | Loop Support |
| Billing queries | billing@loop.ai | Loop Support → auto-tag `billing` |
| Security / abuse | security@loop.ai | Security inbox (private) |
| In-product chat widget | `/api/v1/support/ticket` (POST) | Loop Support |
| Slack Connect (enterprise) | Per-workspace channel | Loop Support → tag `enterprise` |

All tickets routed to the **Loop Support** inbox are visible to the full support team. **Security inbox** is visible only to the security on-call engineer.

---

## 2. Routing rules

Rules are configured inside Front under **Settings → Rules** and evaluated in order.

| Rule ID | Condition | Action |
|---------|-----------|--------|
| SR-001 | Subject contains `[BILLING]` or sender matches `billing@` | Assign to *Billing* sub-inbox; tag `billing` |
| SR-002 | Subject contains `[SECURITY]` or sender matches `security@` | Move to *Security* private inbox; page on-call via PagerDuty |
| SR-003 | Tag `enterprise` AND no assignee after 30 min | Assign to enterprise CSM; send auto-reply |
| SR-004 | SLA timer > 4 h AND status = open | Escalate to support lead; send internal @mention |
| SR-005 | Body matches `/CVE-\d{4}-\d{4}/i` | Auto-tag `security`; move to Security inbox |
| SR-006 | Inbound from `@loop.ai` domain | Tag `internal`; skip SLA timer |

---

## 3. SLA targets

| Tier | First response | Resolution |
|------|---------------|-----------|
| Enterprise (SLA tier 1) | 1 business hour | 8 business hours |
| Growth (SLA tier 2) | 4 business hours | 2 business days |
| Starter (SLA tier 3) | 1 business day | 5 business days |
| Security reports | 24 hours (any day) | Per incident severity |

SLA timers are configured in Front under **Settings → SLAs**.

---

## 4. Ticket lifecycle

```
Inbound → [SR-xxx routing rules] → Assigned inbox
    ↓
Agent picks up ticket (status: Active)
    ↓
First response sent (SLA timer stops for FRT)
    ↓
Resolution reached (status: Resolved) ─── no reply 5 days → Archived
    ↓
CSAT survey sent (3-day delay)
```

---

## 5. Escalation paths

### 5.1 Technical escalation

1. Support agent tags `needs-engineering`.
2. Front rule pages the on-call engineer via PagerDuty integration.
3. Engineer joins the Front conversation thread (no email CC necessary).
4. Resolution notes added to conversation before closing.

### 5.2 Billing / account escalation

1. Tag `billing-escalation`.
2. Front auto-assigns to Finance lead.
3. Finance lead responds within 1 business hour (SLA tier 1 aligned).

### 5.3 Security / abuse escalation

1. Ticket moves to Security inbox automatically via SR-002 / SR-005.
2. PagerDuty alert fires immediately (P1 if subject contains `breach`, `leak`, `CVE`).
3. Follow `engineering/SECURITY.md` → Incident Response procedure.

---

## 6. Runbook: RB-025 — Support inbox overflow

**Owner:** Support lead.  **SEV target:** SEV3 → SEV2 if FRT SLA at risk.

**Symptoms:** Front inbox queue > 50 open tickets; SLA breach alert fires; CSAT dropping below 4.0.

**Steps:**

1. Check Front inbox — identify top ticket categories (`billing`, `technical`, `enterprise`).
2. For `technical` tickets: use the *needs-engineering* escalation path (§ 5.1).
3. For `billing` tickets: alert Finance lead directly on Slack `#finance-alerts`.
4. Send bulk auto-reply to tickets older than 2 h: use Front Canned Response "Queue Delay Notice".
5. If FRT SLA at risk for tier 1 (enterprise) tickets: page support lead via PagerDuty.
6. After queue clears: update SLA timer configuration if overflow was caused by mis-routing.

**Post-incident:**

- Document the overflow cause in `loop_implementation/engineering/RUNBOOKS.md` under RB-025 drill history.
- File follow-up story if routing rules need adjustment.

---

## 7. Testing the integration

### 7.1 Smoke test (run after any Front configuration change)

```bash
# Send a test ticket to support@loop.ai
curl -X POST https://api2.frontapp.com/inboxes/$FRONT_INBOX_ID/imported_messages \
  -H "Authorization: Bearer $FRONT_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sender": { "email": "test-smoke@loop.ai" },
    "to": ["support@loop.ai"],
    "subject": "[TEST] Smoke test — please ignore",
    "body": "Automated smoke test. Discard.",
    "tags": ["smoke-test"]
  }'
# Expected: 202 Accepted; ticket appears in Loop Support inbox with tag smoke-test
```

### 7.2 Routing rule validation

| Test | Input | Expected Front inbox |
|------|-------|---------------------|
| Billing tag | Subject `[BILLING] Invoice query` | Billing sub-inbox + tag `billing` |
| Security tag | Subject `[SECURITY] Possible breach` | Security private inbox |
| CVE pattern | Body contains `CVE-2024-1234` | Security private inbox |
| Internal skip | Sender `alice@loop.ai` | Loop Support + tag `internal` + SLA skipped |
| Enterprise escalation | Tag `enterprise` + no assignee 30 min | CSM assigned + auto-reply sent |

---

## 8. References

- `loop_implementation/engineering/RUNBOOKS.md` — operational runbooks index
- `loop_implementation/engineering/SECURITY.md` — incident response (security tickets)
- Front admin console: https://app.frontapp.com/settings (requires Front admin role)
- PagerDuty service: `loop-support` (escalation policy: support-lead → CTO)
