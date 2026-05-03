# Loop — Penetration Testing Program

**Status:** v0.2 — vendor shortlist + pre-engagement checklist (S919)
**Owners:** Sec eng (program lead), Eng #2 (infra support), CTO (approvals).
**Cadence:** Quarterly (end of each quarter) by an external firm.
**Compliance:** SOC2 CC6.2 — "Security testing and evaluation to identify vulnerabilities and remediation priorities" + ISO 27001 A.14.2.

This document is the master record for Loop's external penetration testing program: vendor selection, scope definition, rules of engagement, staging environment setup, credential management, and post-test remediation tracking.

---

## 1. Vendor selection

**Current vendor:** TBD — Sec eng-led decision after Q2 2026 RFP. Shortlist below; selection target **2026-05-06**, contract signature **2026-05-09**, kickoff **2026-05-13**.

### 1.1 Selection criteria (must-haves)

- **CREST** or equivalent accreditation (PTES, SANS, OSCP depth) — non-negotiable for SOC2 evidence.
- Demonstrated experience pen-testing SaaS multi-tenant Kubernetes environments (≥3 reference engagements in the last 24 months).
- Willingness to sign Loop's mutual NDA + restrictive data-handling addendum within 5 business days of vendor selection.
- Availability of a senior+associate two-person team for the full 2-week window, Mon–Fri only, no holidays.
- Findings deliverable: structured report (CSV/JSON) per finding so remediation rolls into the StoryV2 backlog automatically (see §6.5).
- Mandatory post-test debrief (≥60 min) with Sec eng + Eng #2 + CTO before invoice.

### 1.2 Selection criteria (nice-to-haves)

- Prior LLM/agent-platform exposure (prompt injection, MCP tool sandbox escape, model-output exfiltration).
- Familiarity with the Loop tech stack (Python, FastAPI, NATS, Postgres+RLS, Qdrant, Helm, Kata/runc).
- US East-coast / EU working-hours overlap with Loop on-call (no transatlantic lag for P1 escalation).
- A re-test option at fixed price within 90 days of report delivery for P1/P2 remediation verification.

### 1.3 Candidate matrix (v0.2 shortlist — three CREST-accredited vendors)

The three vendors below were sourced from CREST's published member directory + referrals from the design-partner network. Quoted price ranges are for a single 2-week engagement against the staging cluster scoped per §2; numbers are USD and exclude expenses and re-tests.

| # | Vendor | HQ | Accreditation | SaaS / k8s depth | LLM/agent depth | Price range (2-week) | Re-test | Reference engagement | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **A** | NCC Group | UK / US (multiple offices) | CREST CRT, Cyber Scheme, OSCP/OSCE depth | Strong — k8s + AWS + multi-tenant SaaS engagements published in their case-study library | Limited — no published LLM-pentest case studies but has an "AI red team" service line on the website | **$70k–$95k** | Yes, fixed-price re-test within 60 days | Reference customer-facing SaaS platform on EKS — anonymised case study on file | Largest of the three; longest lead time (4–6 wk). Highest brand value for SOC2 evidence. |
| **B** | Cure53 | Berlin, DE | OSCP, OSCE, BSI-listed | Strong — well-known for browser, web, Kubernetes audits (Mozilla, Cloudflare, GitLab in public reports) | **Best of the three** — public report of LLM/agent pen-tests including jailbreaks, prompt-injection chains, and tool-execution sandbox bypass | **$60k–$80k** | Yes, hourly rate for re-test | Cloudflare Workers + agent platforms (public report) | Strong technical depth. EU timezone. NDA negotiation tends to be quick. |
| **C** | Bishop Fox | US (Phoenix, NYC, remote) | OSCP, GPEN, GXPN, CRTP | Strong — fintech and SaaS heavy (Atlassian, Stripe in published case studies) | Moderate — has done agent + LLM-integrated SaaS audits but most case studies are NDA-protected | **$65k–$90k** | Yes, fixed-price re-test within 90 days | Fintech multi-tenant control plane on EKS | US East working hours. Strong compliance documentation hand-off. |

**Decision matrix (Sec eng to fill before 2026-05-06):**

| Criterion | Weight | NCC Group | Cure53 | Bishop Fox |
| --- | --- | --- | --- | --- |
| LLM/agent depth | 25% | _ / 5 | _ / 5 | _ / 5 |
| K8s / SaaS depth | 20% | _ / 5 | _ / 5 | _ / 5 |
| Price | 15% | _ / 5 | _ / 5 | _ / 5 |
| Re-test terms | 15% | _ / 5 | _ / 5 | _ / 5 |
| SOC2 brand value | 10% | _ / 5 | _ / 5 | _ / 5 |
| Lead time / availability | 10% | _ / 5 | _ / 5 | _ / 5 |
| References reachable | 5% | _ / 5 | _ / 5 | _ / 5 |
| **Total** | 100% | **_ / 5** | **_ / 5** | **_ / 5** |

The CTO signs off on the highest-scoring vendor and authorises the contract. If two vendors tie within 0.2 points, Sec eng calls the highest-priority reference for each and uses that conversation as the tiebreaker.

### 1.4 Historical record

| Quarter | Vendor | Start date | End date | Findings (P1/P2/P3) | Tracking | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Q2 2026 | TBD (selection due 2026-05-06) | 2026-05-13 | 2026-05-24 | — | — | Scheduled |

---

## 1A. Pre-engagement checklist (sign-off block)

This is the canonical checklist the CTO signs **before the vendor is allowed onsite-equivalent (VPN) access to staging**. Every item must be ticked or marked N/A with rationale; the signed copy is committed to `loop_implementation/operations/PENTEST_Q<n>_<yyyy>_SIGNOFF.md` (gitignored if it contains anything sensitive; otherwise checked in).

```
Vendor selected:        ___________________________  (per §1.3 decision matrix)
Engagement window:      ____-__-__  to  ____-__-__   (2 calendar weeks, Mon–Fri only)
Scope freeze date:      ____-__-__                   (≥ 5 business days before kickoff;
                                                      no §2 changes accepted after this)
Sec eng signature:      ___________________________  Date: ____-__-__
Eng #2 signature:       ___________________________  Date: ____-__-__
CTO signature:          ___________________________  Date: ____-__-__
```

### 1A.1 Legal & paperwork

- [ ] **Mutual NDA** signed by both parties. Template lives at
      [`loop_implementation/legal/NDA_PENTEST_TEMPLATE.md`](../legal/NDA_PENTEST_TEMPLATE.md)
      (create on first engagement; subsequent engagements re-use the
      master signed by Loop's General Counsel).
- [ ] **Data-handling addendum** signed: vendor acknowledges no data
      leaves their secure facility, all artefacts encrypted at rest with
      a key under their custody, full destruction within 30 days of
      report delivery, attestation email to Sec eng.
- [ ] **Master Services Agreement (MSA)** signed if this is the first
      engagement with this vendor; otherwise re-use SOW under existing MSA.
- [ ] **Statement of Work (SOW)** signed including: scope per §2, RoE
      per §3, deliverables per §1.1, price + payment terms, re-test
      option, indemnity caps.
- [ ] **Insurance certificate** (E&O ≥ $5M, Cyber ≥ $5M) on file.
- [ ] **Per-tester background-check attestation** received from vendor
      for every individual who will receive Loop credentials.

### 1A.2 Scope freeze

- [ ] §2.1 in-scope systems list reviewed and agreed by Sec eng + Eng #2
      + CTO. Frozen at the **scope freeze date** above.
- [ ] §2.2 out-of-scope list reviewed and agreed.
- [ ] §2.3 vendor scope-acknowledgement signed and filed under §6.1.
- [ ] **No mid-engagement scope expansion.** Anything discovered that
      would extend the scope is documented as a follow-up engagement
      proposal and triaged after report delivery — never expanded inside
      the active 2-week window.

### 1A.3 Rules-of-engagement document

- [ ] §3 RoE document (this file, §3.1–3.5) reviewed line-by-line with
      vendor lead in a 60-minute call. Recording archived under
      `s3://loop-pentest-archive/<quarter>/roe-walkthrough.mp4`.
- [ ] **Testing window** in §3.1 confirmed against vendor calendar; no
      conflicts with vendor holidays, customer freeze windows, or Loop's
      own change-freeze (release-please calendar).
- [ ] **Communication channel** `#pentest-q<N>-<yyyy>-staging` created
      in Slack; vendor's lead invited as guest with @-mention disabled.
- [ ] **Escalation matrix** §3.5 confirmed: vendor has CTO + on-call
      pager number + backup contact.

### 1A.4 Staging environment stand-up (Eng #2 owns)

- [ ] **Cluster deployed** from production Helm chart with the variances
      noted in §4.1 (replicas = 1, PVs = local, cost optimisations).
      Follow [`infra/helm/loop/values-staging.yaml`](../../infra/helm/loop/values-staging.yaml).
- [ ] **Service versions** match production deploy on the engagement
      kickoff date. Recorded as a `kubectl get deploy -o
      jsonpath='{...}'` snapshot in the sign-off file.
- [ ] **Sample data** loaded: 10 test workspaces, 5 agents per workspace,
      100 turns per agent. Seeding script: `tools/seed_dev.py` plus a
      pen-test-specific overlay at `tools/seed_pentest_data.py`.
- [ ] **Dependencies healthy**: `pg_isready`, `redis-cli ping`, Qdrant
      `/readyz`, NATS `/healthz`, MinIO `/minio/health/ready`,
      ClickHouse `/ping` all green for ≥ 30 minutes. Healthz dump
      committed to sign-off.
- [ ] **TLS** for `staging.loop.example` valid for ≥ 30 days beyond
      engagement end date. cert-manager renewal countdown ≥ 60 days.
- [ ] **Logging fan-out** confirmed by tailing the staging log group and
      generating one synthetic event per service.
- [ ] **Vault** unsealed; KMS key reachable from staging cluster
      (test by minting + decrypting one envelope).
- [ ] **Network policies** in place: staging egress only via the
      pentest-egress-proxy `10.100.50.0/24`; ingress only from
      `vpn.loop.example`.
- [ ] **Monitoring** routed to the staging alert channel; thresholds
      mirror prod so anomalies surface during the test.
- [ ] **Honeypots** §3.4 deployed and the vendor briefed on them.
- [ ] **Alert suppression window** scheduled in PagerDuty for the
      engagement window so the on-call rotation knows to expect noise.
- [ ] Sec eng + Eng #2 sign off in the sign-off file confirming all
      checks above.

### 1A.5 Credential rotation policy (Sec eng owns)

This is the **canonical credential lifecycle** for every pen-test
engagement. It supersedes ad-hoc credential issuance.

**Pre-test (T-7 days):**

- [ ] Generate a per-engagement service account scoped to staging only,
      tagged `pentest=q<N>_<yyyy>`, with read-only scopes per §5.1.
      Command:
      ```bash
      loop admin user create-service-account \
          --name="pentest-q<N>-<yyyy>" \
          --org="staging" \
          --scopes="read:agents,read:evals,read:turns" \
          --expires-at="<engagement-end>T17:00:00Z"
      ```
- [ ] Deliver API key + secret to vendor through one channel only:
      a one-time-view password-manager link (Bitwarden Send / 1Password
      shared item) signed for by the vendor lead. **No email, no Slack,
      no plaintext anywhere.**
- [ ] Issue VPN credentials (`vpn.loop.example`) to each named
      pen-tester on the engagement; require 2FA.
- [ ] Log issuance metadata (key ID, scopes, expiry — no secret) to
      `s3://loop-pentest-archive/<quarter>/credentials-issued.json`.

**During-test (continuous):**

- [ ] Daily audit-log review at 09:30 UTC: query `loop admin audit
      list --service-account=pentest-q<N>-<yyyy>` and confirm only
      in-scope endpoints are being hit. Anomalies → P2 finding.

**Post-test (T+0, within 2 hours of engagement close):**

- [ ] Revoke the pen-test service account immediately:
      ```bash
      loop admin user delete-service-account --id=pentest-q<N>-<yyyy>
      ```
- [ ] Rotate **all** other staging API keys, Vault tokens, and
      service-credential refresh tokens issued before/during the
      engagement (assume any of them could have been observed in
      transit even though the testers had no reason to capture them).
- [ ] Deactivate every VPN account issued to the vendor's individual
      testers.
- [ ] Email post-test attestation to vendor lead: "credentials revoked,
      VPN deactivated, audit log archived" — vendor counter-signs
      confirming destruction of any cached credentials on their side.
- [ ] Export the engagement audit log to
      `s3://loop-pentest-archive/<quarter>/audit-log.json.gz` and run
      anomaly review (queries outside the declared scope, time
      anomalies, parameter-fuzzing patterns inconsistent with the
      report). File any new findings as P2/P3.
- [ ] Update §1.4 historical-record table with vendor name, dates,
      finding counts, tracking links, and status.

### 1A.6 Final go/no-go checklist

The kickoff call happens **only when all of these are true**:

- [ ] §1A.1 Legal & paperwork — every box ticked or N/A justified.
- [ ] §1A.2 Scope frozen on or before the freeze date.
- [ ] §1A.3 RoE walkthrough completed and recorded.
- [ ] §1A.4 Staging environment stood up and signed off (Sec eng +
      Eng #2 + CTO signatures in the sign-off file).
- [ ] §1A.5 Credentials issued via one-time-view channel only;
      vendor confirmed receipt in writing.
- [ ] **Backout plan** acknowledged: if any of the above is incomplete
      at T-24h, the engagement is delayed by 1 week (vendor SOW must
      include this clause). No "we'll fix it during week 1" allowed.

If ANY box is unchecked at the go/no-go meeting (T-24h before kickoff),
the engagement is rescheduled. There is no partial start.

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
