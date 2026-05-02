# Loop — Penetration Testing Program

**Status:** v0.1  •  **Owners:** Sec eng (program lead), Eng #2 (infra support), CTO (approvals).
**Cadence:** Quarterly (end of each quarter) by an external firm.
**Compliance:** SOC2 CC6.2 — "Security testing and evaluation to identify vulnerabilities and remediation priorities" + ISO 27001 A.14.2.

This document is the master record for Loop's external penetration testing program: vendor selection, scope definition, rules of engagement, staging environment setup, credential management, and post-test remediation tracking.

---

## 1. Vendor selection

**Current vendor:** (TBD — S576 stage: vendor scope discussion in progress)

Criteria for vendor selection:
- CREST or equivalent accreditation (PTES, SANS, OSCP depth).
- Experience with SaaS multi-tenant Kubernetes environments.
- Willingness to sign NDA + restrictive data handling addendum.
- Availability within the scheduled 2-week window (Mon–Fri only, no holidays).

**Historical record:**

| Quarter | Vendor | Start date | End date | Findings (P1/P2/P3) | Tracking | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Q2 2026 | TBD | 2026-05-13 | 2026-05-24 | — | — | Scheduled |

---

## 2. Scope agreement

### 2.1 In-scope systems

The pen-test covers the following components of the production-like staging environment:

- **Control plane:** `cp-api`, `cp-deploy`, `cp-gateway` services in the staging cluster.
- **Data plane:** `dp-runtime`, `dp-gateway`, tool sandbox isolation (but NOT the actual LLM calls — those are mocked).
- **Data layer:** Postgres logical cluster, Redis, Qdrant (read-only tests only — no data modification).
- **Observability:** OTel pipeline, Prometheus scrape endpoints (no credential dump from metrics).
- **Authentication:** OIDC/SAML flow (if applicable), API key management, session handling.
- **Network:** Ingress + egress filtering, network policies, DDoS mitigations (traffic shaping, rate limits).
- **Secrets management:** Vault access controls, KMS envelope encryption, key rotation.

### 2.2 Out-of-scope

The following are explicitly out-of-scope to keep the test feasible in 2 weeks:

- **Live production environment** — pen-test runs against staging only; no production network access.
- **Customer data** — no real customer workspaces; all test data is synthetic.
- **Social engineering** — no phishing, call attempts, or physical intrusion.
- **Third-party dependencies** — Kubernetes upstream, Go stdlib, Helm charts are assume trusted (CVE scanning is a separate program).
- **AI model behavior** — LLM calls are stubbed; no adversarial prompts or jailbreak attempts.
- **Mobile/web frontend** — studio/desktop clients not tested; focus is backend API + service-to-service auth.

### 2.3 Vendor sign-off

The vendor must provide a signed **Scope Acknowledgement** confirming they have read §2.1–2.2. This is attached as an appendix to this document upon receipt (see §6).

---

## 3. Rules of Engagement (RoE)

### 3.1 Testing windows

- **Approved testing dates:** 2026-05-13 (Tue) through 2026-05-24 (Sat), 09:00–17:00 UTC each day.
- **No testing outside these windows.** If the vendor identifies a critical finding near end-of-day Friday, they MUST NOT continue testing; document the finding and halt immediately. Resume Monday AM per the escalation protocol in §3.5.
- **Holiday skip:** If a testing day falls on a company holiday (loop.example holiday calendar observed), the test window extends by one day at the end.

### 3.2 Communication protocol

- **Slack channel:** `#pentest-q2-2026-staging` (vendor invited as guest; no @channel pings).
- **Daily check-in:** 09:15 UTC each morning. Vendor confirms systems online + baseline connectivity OK.
- **Incident reporting:** If a test crashes a service or corrupts data, vendor reports to `#pentest-q2-2026-staging` **immediately** (≤5 min). Sec eng triages. If customer data is affected → escalate to CTO within 1 hour.
- **Closing meeting:** Final day (Fri 2026-05-24) at 17:00 UTC. Vendor presents preliminary findings; Sec eng + Eng #2 present. Recording for async review.

### 3.3 Access controls

- **Staging environment isolation:** Pen-testers have credentials scoped to staging namespace only. Zero access to production clusters/VPCs.
- **Network isolation:** Pen-test traffic is routed through a dedicated egress proxy (`10.100.50.0/24`) which is separate from production egress. IDS/WAF rules are RELAXED for this test window (see §3.4) but traffic is still logged for post-test review.
- **Credential scope:** API keys issued to pen-testers are tagged with `pentest=q2_2026` and scoped to read-only where feasible (e.g., list agents, read eval results; no deploy/delete).
- **VPN / bastion:** Pen-testers must always connect via the corporate VPN (`vpn.loop.example`) + 2FA. No direct internet→staging connections.

### 3.4 Defensive posture during testing

To allow meaningful testing without compromising production:

- **Alert suppression:** Sec eng team acknowledges and MUTES prod + staging alerts for Slack notifications during test window. Syslog/centralized logging stays enabled. Real-time EDR is still active.
- **WAF/IDS rules:** Staging environment has permissive WAF rules (all traffic logged, few blocks). Production WAF rules remain strict.
- **Rate limiting:** Staging rate limits are relaxed 10× (e.g., 1000 reqs/min instead of 100) to allow rapid scanning. This is temporary and reverted at test end.
- **Honeypots:** Staging contains a fake SSH service on port 22 and a fake database on port 5432 (jailing any commands). These are NOT production services and are known to the vendor in advance.

### 3.5 Escalation matrix

| Severity | Finding | Action | Escalation | Timeline |
| --- | --- | --- | --- | --- |
| **P1 — Critical** | RCE, auth bypass, data exfiltration | STOP testing immediately. Isolate staging cluster. | CTO + CEO page (via incident) | ≤1 h |
| **P2 — High** | Unauth API endpoints, crypto weakness, privilege escalation | Log finding, document + reproduce. Pen-test CONTINUES. | Sec eng review + optional brief to CTO | ≤ 4 h |
| **P3 — Medium** | XSS, CSRF, enumeration | Log finding; pen-test continues. | Included in final report | End of window |

**Remediation SLA:** P1 findings are addressed within 2 weeks of report; P2 within 4 weeks; P3 within 8 weeks.

---

## 4. Staging environment setup

### 4.1 Provisioning checklist

Before testing begins, the **staging ops team** (Eng #2 lead) completes this checklist:

- [ ] Staging cluster deployed from the same Helm chart as production (except service replicas = 1, PVs = local, cost optimizations).
- [ ] All Loop services at the same version as the prod deploy on the test start date.
- [ ] Sample data loaded: 10 test workspaces, 5 agents per workspace, 100 turns per agent (representative of prod).
- [ ] Postgres replicas, Redis sentinels, Qdrant shards all configured and healthy (not degraded).
- [ ] TLS certificates for `staging.loop.example` valid for ≥ 30 days beyond test end date.
- [ ] Centralized logging (CloudWatch / DataDog / Splunk) enabled and fanning to a dedicated staging log group.
- [ ] Vault unsealed; KMS key reachable.
- [ ] Secrets synced from prod template (but with staging-only creds — database passwords, API keys unique to staging).
- [ ] Network policies in place: staging egress only to the designated proxy; ingress only from pen-test VPN.
- [ ] Monitoring + alerting for staging pointed to the staging alert channel; all threshold levels the same as prod (to detect anomalies).

**Approval gate:** Sec eng + Eng #2 sign off (in a commit message) that the staging environment matches prod layout + all systems are green. This is appended to this document (see §6).

### 4.2 Baseline documentation

The pen-testers receive (by email, day before test starts):

1. **ARCHITECTURE.md** — system components, data flow diagrams.
2. **Staging environment connectivity guide** — IP ranges, DNS, VPN config.
3. **API documentation** — OpenAPI spec (exported from production, applicable to staging).
4. **Secrets management guide** — Vault structure (read-only), KMS key setup.
5. **Known issues log** — a list of findings from the prior pen-test that are intentionally NOT fixed (to avoid scope creep).

---

## 5. Credential management

### 5.1 Pre-test credential issuance

One week before testing:

- **Sec eng** generates pen-test service account:
  ```
  loop admin user create-service-account \
    --name="pentest-q2-2026" \
    --org="staging" \
    --scopes="read:agents,read:evals,read:turns" \
    --expires-at="2026-05-25T17:00:00Z"
  ```
- API key + secret exported to a secure channel (encrypted email, shared password manager entry shared to vendor via Okta/AnyDesk session).
- Sec eng logs the issuance: `s3://loop-pentest-archive/2026-q2/credentials-issued.json` (contains key ID, scopes, expiry — no secrets).

### 5.2 Credential rotation (post-test)

Within 2 hours of the test window closing (2026-05-24 17:00 UTC):

- **Sec eng** revokes the pen-test service account:
  ```bash
  loop admin user delete-service-account --id=pentest-q2-2026
  ```
- Logs the revocation: `s3://loop-pentest-archive/2026-q2/credentials-revoked.json`.
- **All other API keys** in staging are rotated (Vault-backed service credentials, GitHub secrets, etc.) to be safe.
- The VPN account given to pen-testers is deactivated.
- Post-test attestation email sent to pen-test vendor + Sec eng team confirming revocation.

### 5.3 Credential audit trail

Audit logs for the pen-test service account during the test window are exported to:
```
s3://loop-pentest-archive/2026-q2/audit-log.json.gz
```

These are reviewed **post-test** for any anomalous access patterns (e.g., queries outside the declared scope). If found, a P2 or P3 finding is filed.

---

## 6. Appendices (to be filled post-S576 claim)

### 6.1 Vendor scope acknowledgement

_(Attached upon vendor confirmation. Contains vendor name, contact, accreditation ID, signed date, and confirmation that they have reviewed §2.1–2.2.)_

### 6.2 Staging environment sign-off

_(Attached upon Sec eng + Eng #2 approval. Contains cluster version, service versions, test data snapshot, baseline alert confirmation, timestamp.)_

### 6.3 Test start notification

_(Sent to all-hands Slack at 2026-05-13 09:00 UTC with: vendor name, test window, escalation contacts, alert suppression period, link to #pentest channel.)_

### 6.4 Test end summary

_(Appended within 24 h of 2026-05-24 17:00 UTC. Contains: test completion timestamp, preliminary finding count by severity, vendor hand-off confirmation, credential revocation confirmation.)_

### 6.5 Final remediation tracking

_(Linked to the open GitHub epic E16 "SOC2 compliance". Each P1/P2/P3 finding from the pen-test becomes a StoryV2 with the `pentest-remediation` tag. The epic tracks these to Done status.)_

---

## 7. Compliance mapping

| Standard | Control | Evidence |
| --- | --- | --- |
| SOC2 CC6.2 | Security testing and evaluation | This document + test results + remediation tracking |
| ISO 27001 A.14.2 | Vulnerability assessment | Pen-test + prior CVE scanning program |
| GDPR Art. 32 | Security testing of processing systems | Attestation from vendor (§6.1) |

This document is the durable artifact for those controls. Vanta evidence collector pulls links from §6 automatically.
