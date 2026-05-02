# SOC 2 Type 1 — Kickoff & Tracker

> Status: **kickoff**, vendor: **Vanta**.
> Owner: Security Engineer. Auditor: TBD (Vanta-recommended pool).
> Target Type 1 report date: end of Q3.
> Type 2 observation window opens immediately after Type 1 issue.

This is the working tracker for the SOC 2 Type 1 audit. It maps
every Trust Services Criterion (TSC) we are in scope for to a
control owner, evidence source, and current status. **All
narrative responses to questionnaires must cite a control row in
this document** so reviewers can trace claim → evidence.

See also:

* [SECURITY.md](SECURITY.md) — engineering threat model and
  baseline controls (the *implementation* side).
* [DR.md](DR.md) — availability and recovery runbook.
* [REGIONAL_DEPLOYS.md](REGIONAL_DEPLOYS.md) — residency posture.

## Scope

| Item                       | Decision                                                     |
| -------------------------- | ------------------------------------------------------------ |
| Trust Services Criteria    | **Security** (Common Criteria) only for Type 1               |
| Additional TSCs (Type 2)   | Availability + Confidentiality (planned, post-Type-1)        |
| Systems in scope           | control-plane, runtime, gateway, kb-engine, channels,         |
|                            | studio, infra/helm/loop, all CI/CD pipelines                 |
| Production environments    | us-east (primary), eu-west (S045)                            |
| Data classes               | customer prompts, tool-call payloads, agent outputs, audit logs |
| Out of scope (Type 1)      | sales CRM, finance ledger, marketing site                    |
| Auditor                    | TBD — Vanta-managed shortlist, decision by end of week       |
| Vendor of record (GRC)     | Vanta                                                        |

## Roles & RACI

| Role                 | Person          | Notes                                 |
| -------------------- | --------------- | ------------------------------------- |
| Executive sponsor    | CEO             | Signs management assertion            |
| Audit lead           | Security Eng    | Drives the program; Vanta primary     |
| Engineering owner    | Founding eng    | Code controls, CI/CD, infra           |
| HR/People owner      | Founding ops    | Onboarding/offboarding, training      |
| IT owner             | Founding ops    | Endpoint MDM, MFA, identity provider  |
| Legal owner          | Outside GC      | DPAs, vendor agreements               |
| Auditor liaison      | Security Eng    | All evidence requests routed through  |

## Vanta integration checklist

> The OAuth handshake by which Loop links a workspace to a Vanta
> organization is specified separately in
> [VANTA_INTEGRATION.md](VANTA_INTEGRATION.md) (S570). The table below
> tracks the inverse: what Vanta connects to *inside* Loop.

| Integration            | Status      | Notes                                |
| ---------------------- | ----------- | ------------------------------------ |
| Identity provider (IdP)| ☐ pending   | Okta / Google Workspace TBC          |
| Source control (GitHub)| ☐ pending   | Org-level install + branch protection |
| CI/CD                  | ☐ pending   | GitHub Actions environments + reqd reviews |
| Cloud provider         | ☐ pending   | AWS Org or GCP Org read-only role    |
| MDM                    | ☐ pending   | Kandji / Jamf / Intune TBC           |
| HRIS                   | ☐ pending   | Rippling / Gusto TBC                 |
| Background-check vendor| ☐ pending   | Checkr or similar                    |
| Vulnerability scanner  | ☐ pending   | Vanta-bundled or Snyk                |
| Vendor-risk module     | ☐ pending   | Inventory of subprocessors           |

## Evidence sources index

Every control row in §"Control families" lists where the evidence
lives. This index is the inverse map: each engineering-managed
evidence source → where it is produced, where it is stored, which
controls it satisfies, and how the auditor (or Vanta) pulls it.

The auditor pull pattern is uniform: download the latest green CI
artifact / read the file at the listed path on `main`. Production
control evidence (cloud / IdP / MDM) is collected by the Vanta agents
listed in the previous section and lives outside this repo.

| Evidence source                              | Produced by                                                 | Repo path / artifact name                                     | Controls satisfied | Auditor pull                                                                |
| -------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------- | ------------------ | --------------------------------------------------------------------------- |
| Branch protection + CODEOWNERS               | GitHub repo settings                                        | `docs/branch-protection.md` + GitHub UI                       | CC5.1, CC5.3, CC8.1 | GH org settings export                                                      |
| CI green-status history                      | GitHub Actions                                              | `.github/workflows/ci.yml`; Actions runs                      | CC8.1, CC8.2        | GH Actions API: list runs on `main` per quarter                             |
| Filesystem vuln scan (trivy, blocking HIGH+) | `security` job, `aquasecurity/trivy-action`                 | `.github/workflows/ci.yml` (S579)                             | CC7.1               | CI run logs → "Filesystem vuln scan (trivy)" step                           |
| SCA gate (snyk, threshold=high)              | `security` job, `snyk/actions/python` (token-gated)         | `.github/workflows/ci.yml` (S579)                             | CC7.1, CC7.2        | CI run logs → "Snyk dependency scan" step + Snyk dashboard                  |
| Secrets-scanning gate (gitleaks)             | `security` job, `gitleaks/gitleaks-action`                  | `.github/workflows/ci.yml` + `.gitleaks.toml` (S580)          | CC6.1, CC7.1        | CI run logs → "Secrets scan (gitleaks)" step + uploaded gitleaks artifact   |
| SBOM (CycloneDX 1.5 JSON)                    | `security` job, `anchore/sbom-action`                       | artifact `sbom-cyclonedx`, file `sbom.cdx.json` (S578)        | CC7.1, CC7.2, CC9.1 | Download `sbom-cyclonedx` artifact from each green CI run                   |
| Threat model + security policy               | Engineering                                                 | `loop_implementation/engineering/SECURITY.md`                 | CC2.1, CC3.2        | git log of SECURITY.md (review cadence verified by commit history)         |
| Incident-response runbook                    | Engineering                                                 | `loop_implementation/engineering/RUNBOOKS.md`                 | CC2.2, CC7.4        | Read file on `main`                                                         |
| DR runbook + drill log                       | Engineering (S575)                                          | `loop_implementation/engineering/DR.md`                       | CC7.5               | Read file on `main` + last-drill timestamp in change log                    |
| Migration discipline (reversible/flagged)    | Alembic templates                                           | `data/SCHEMA.md` + migration files                            | CC8.3               | Inspect migration files for `downgrade()` body                              |
| Tenant data segregation (RLS)                | Postgres policies + integration tests                       | `data/SCHEMA.md` §RLS + `_tests_integration/test_postgres_*`  | CC6.7               | Read schema + green test runs                                               |
| Encryption at rest + in transit              | Helm values + cloud KMS                                     | `infra/helm/loop/values.yaml` + cloud-provider key inventory  | CC6.6               | Helm values diff + cloud KMS export                                         |
| Audit-trail completeness                     | `audit_log` table + emit-on-state-change discipline (S581)  | `data/SCHEMA.md` §audit + `loop_control_plane/audit/`         | CC4.1, CC6.x        | SQL: `SELECT count(*) … per state-change type per day`                      |
| SOC2 Type 1 attestation                      | External auditor (S582)                                     | Signed PDF (delivered out-of-band)                            | All families        | Auditor portal                                                              |

## Control families

Each row owns its evidence path, refresh cadence, and Vanta test ID.

### CC1 — Control environment

| ID    | Control                                            | Owner       | Evidence                                       | Status |
| ----- | -------------------------------------------------- | ----------- | ---------------------------------------------- | ------ |
| CC1.1 | Code of conduct signed by all employees            | People      | HRIS attestations                              | ☐      |
| CC1.2 | Security awareness training annually + on hire     | People      | Vanta training module completion records       | ☐      |
| CC1.3 | Org chart maintained, reviewed quarterly           | People      | HRIS export                                    | ☐      |
| CC1.4 | Background check before access to production       | People      | Checkr reports (gated in onboarding workflow)  | ☐      |
| CC1.5 | Performance reviews include security competence    | People      | HRIS review templates                          | ☐      |

### CC2 — Communication & information

| ID    | Control                                            | Owner       | Evidence                                       | Status |
| ----- | -------------------------------------------------- | ----------- | ---------------------------------------------- | ------ |
| CC2.1 | Security policies published, reviewed annually     | Sec Eng     | Internal handbook + version history            | ☐      |
| CC2.2 | Incident-response process documented               | Sec Eng     | RUNBOOKS.md §incident                          | partial — runbook exists, needs SOC2 mapping |
| CC2.3 | Customer-facing security page                      | Sec Eng     | loop.dev/security (TBD)                        | ☐      |

### CC3 — Risk assessment

| ID    | Control                                            | Owner       | Evidence                                       | Status |
| ----- | -------------------------------------------------- | ----------- | ---------------------------------------------- | ------ |
| CC3.1 | Annual risk assessment, signed by CEO              | Sec Eng     | Vanta risk register                            | ☐      |
| CC3.2 | Threat model reviewed every release-train          | Sec Eng     | SECURITY.md change log                         | partial |
| CC3.3 | Vendor inventory + risk-tier classification        | Sec Eng     | Vanta vendor module                            | ☐      |

### CC4 — Monitoring activities

| ID    | Control                                            | Owner       | Evidence                                       | Status |
| ----- | -------------------------------------------------- | ----------- | ---------------------------------------------- | ------ |
| CC4.1 | Continuous control monitoring (Vanta)              | Sec Eng     | Vanta dashboard screenshots, monthly           | ☐      |
| CC4.2 | Internal control testing prior to audit            | Sec Eng     | Test plan + evidence pack                      | ☐      |

### CC5 — Control activities

| ID    | Control                                            | Owner       | Evidence                                       | Status |
| ----- | -------------------------------------------------- | ----------- | ---------------------------------------------- | ------ |
| CC5.1 | Change-management policy enforced via PR review    | Eng         | GitHub branch protection + CODEOWNERS          | partial |
| CC5.2 | Production deploys require approval                | Eng         | GH Actions environment protection rules        | ☐      |
| CC5.3 | Separation of duties: no developer self-approves   | Eng         | CODEOWNERS + branch protection                 | ☐      |

### CC6 — Logical & physical access

| ID    | Control                                            | Owner       | Evidence                                       | Status |
| ----- | -------------------------------------------------- | ----------- | ---------------------------------------------- | ------ |
| CC6.1 | SSO + MFA enforced on all production tooling       | IT          | IdP policy export                              | partial |
| CC6.2 | Least-privilege IAM, reviewed quarterly            | Eng         | Cloud-provider IAM export                      | ☐      |
| CC6.3 | Onboarding/offboarding workflows                   | People + IT | HRIS-driven IdP provisioning                   | ☐      |
| CC6.4 | Endpoint MDM with disk encryption + screen lock    | IT          | MDM compliance report                          | ☐      |
| CC6.5 | Production data accessed only via bastion / SSO    | Eng         | Audit logs for bastion sessions                | ☐      |
| CC6.6 | Encryption at rest (KMS) and in transit (TLS 1.3)  | Eng         | Helm chart values + cloud provider evidence    | done — see SECURITY.md §encryption |
| CC6.7 | Customer data segregation (per-tenant RLS)         | Eng         | Postgres policy DDL + integration tests        | done — see data/SCHEMA.md §RLS |
| CC6.8 | Anti-malware on endpoints                          | IT          | MDM compliance report                          | ☐      |

### CC7 — System operations

| ID    | Control                                            | Owner       | Evidence                                       | Status |
| ----- | -------------------------------------------------- | ----------- | ---------------------------------------------- | ------ |
| CC7.1 | Vulnerability scanning on every PR                 | Eng         | `.github/workflows/ci.yml` `security` job: trivy fs (S579), snyk (S579), gitleaks (S580), SBOM (S578) | done — see Evidence sources index |
| CC7.2 | Critical CVEs remediated within SLA                | Eng         | Vanta vuln tracker                             | ☐      |
| CC7.3 | 24/7 on-call rotation                              | Eng         | PagerDuty schedule                             | partial |
| CC7.4 | Incident post-mortems, blameless                   | Eng         | RUNBOOKS.md template                           | partial |
| CC7.5 | Backup + restore tested quarterly                  | Eng         | DR.md drill log                                | partial |

### CC8 — Change management

| ID    | Control                                            | Owner       | Evidence                                       | Status |
| ----- | -------------------------------------------------- | ----------- | ---------------------------------------------- | ------ |
| CC8.1 | All code changes via PR with peer review           | Eng         | GitHub PR history                              | done   |
| CC8.2 | Automated tests pass before merge                  | Eng         | GitHub branch protection requires `lint` + `unit` + `tracker-clean` + `security` jobs in `.github/workflows/ci.yml`; see `docs/branch-protection.md` | done   |
| CC8.3 | Production migrations reversible or feature-flagged| Eng         | Migration template in data/                    | partial |

### CC9 — Risk mitigation (vendors)

| ID    | Control                                            | Owner       | Evidence                                       | Status |
| ----- | -------------------------------------------------- | ----------- | ---------------------------------------------- | ------ |
| CC9.1 | Subprocessor list published + DPAs signed          | Legal       | loop.dev/subprocessors                         | ☐      |
| CC9.2 | Vendor risk-tier reviews annually                  | Sec Eng     | Vanta vendor module                            | ☐      |

## Evidence collection cadence

| Cadence    | Items                                                                 |
| ---------- | --------------------------------------------------------------------- |
| Continuous | Vanta integrations (IdP, GitHub, cloud, MDM)                          |
| Weekly     | Vanta dashboard review, control-status update in this doc             |
| Monthly    | Access reviews (production IAM, prod database, GitHub admins)         |
| Quarterly  | Risk assessment review, DR drill, vulnerability remediation review    |
| Annually   | Security awareness training, policy refresh, vendor review            |

## Key milestones

| Milestone                                  | Target       | Status  |
| ------------------------------------------ | ------------ | ------- |
| Vanta workspace provisioned                | Week 0       | ☐       |
| All Vanta integrations live                | 2026-05-16   | ☐       |
| Policy set published internally            | 2026-06-06   | ☐       |
| Security training pushed to all staff      | 2026-06-13   | ☐       |
| First control gap closed (CC6.x suite)     | 2026-06-06   | ☐       |
| Auditor selected and engaged               | 2026-05-09   | ☐       |
| Internal pre-audit walkthrough             | 2026-06-20   | ☐       |
| Kickoff meeting held                       | 2026-05-02   | ✅ done |
| Type 1 audit fieldwork                     | 2026-07-07–18 | ☐       |
| Type 1 report issued                       | 2026-07-31   | ☐       |
| Type 2 observation window opens            | 2026-08-01   | ☐       |

## Out-of-scope clarifications

* **HIPAA / BAA** is *not* in scope for this audit. HIPAA-track work
  is sequenced after Type 2 issuance.
* **FedRAMP** is *not* in scope. Tracked on a separate program.
* **PCI** is *not* applicable; Loop never handles cardholder data.

---

## Kickoff meeting

**Date:** 2026-05-02 (synthetic baseline — first formal sync)
**Duration:** 90 min
**Chair:** Security Engineer
**Attendees:** CEO (executive sponsor), Security Engineer (audit lead), Founding Engineer (engineering owner), Founding Ops (HR/IT/People owner), Outside General Counsel (legal owner), Auditor liaison (Security Engineer doubles as liaison)
**Auditor firm:** TBD — shortlist of three firms from Vanta-recommended pool circulated same day; selection decision by 2026-05-09

### Agenda items

| # | Topic | Outcome |
| --- | --- | --- |
| 1 | Scope confirmation | Security TSC only for Type 1; Availability + Confidentiality deferred to Type 2 |
| 2 | Audit window dates | Type 1 fieldwork: 2026-07-07 to 2026-07-18; report target: 2026-07-31 (see §Audit window & key dates) |
| 3 | Evidence list walkthrough | Full list reviewed; owners confirmed per control row (see §Evidence list — Type 1 pack) |
| 4 | Vanta integration timeline | All integrations live by 2026-05-16; Vanta test runs green by 2026-05-23 |
| 5 | Gap prioritisation | Three open gaps confirmed: CC1.x (people controls, onboarding/training), CC5.2/CC5.3 (deploy approval, separation of duties), CC6.3/CC6.5 (bastion access logging). Remediation owned by Founding Ops + Eng #2 |
| 6 | Communication protocol | Evidence requests routed via Security Engineer only; auditor gets read-only Vanta workspace access |
| 7 | Management assertion | CEO to sign management assertion 1 week before report issue date |

### Decisions

- Auditor selection decision date: **2026-05-09**
- Evidence freeze date (snapshot for fieldwork): **2026-07-04**
- All Vanta integrations must be live and green before evidence freeze
- Fieldwork briefing document (architecture + data flows) to be sent to auditor: **2026-06-27**

---

## Audit window & key dates

| Date | Milestone | Owner | Status |
| --- | --- | --- | --- |
| 2026-05-02 | Kickoff meeting held | Security Eng | ✅ done |
| 2026-05-09 | Auditor firm selected and engagement letter signed | CEO + Security Eng | ☐ |
| 2026-05-16 | All Vanta integrations live | IT + Eng | ☐ |
| 2026-05-23 | Vanta tests all green (or exceptions documented) | Security Eng | ☐ |
| 2026-06-06 | Policy set published internally (all staff acknowledge) | Security Eng | ☐ |
| 2026-06-13 | Security awareness training completed by all staff | People | ☐ |
| 2026-06-20 | Internal pre-audit walkthrough (Security Eng + Founding Eng) | Security Eng | ☐ |
| 2026-06-27 | Fieldwork briefing document (architecture + data flows) sent to auditor | Security Eng | ☐ |
| 2026-07-04 | Evidence freeze — snapshot taken for all in-scope controls | Security Eng | ☐ |
| 2026-07-07 | Audit fieldwork begins | Auditor | ☐ |
| 2026-07-18 | Audit fieldwork ends | Auditor | ☐ |
| 2026-07-24 | Auditor draft report delivered | Auditor | ☐ |
| 2026-07-28 | Loop management response to draft (factual corrections only) | CEO + Security Eng | ☐ |
| 2026-07-31 | Type 1 report issued (signed PDF) | Auditor | ☐ |
| 2026-08-01 | Type 2 observation window opens | Security Eng | ☐ |

---

## Evidence list — Type 1 pack

The following evidence items must be assembled and reviewed before the evidence freeze date (2026-07-04). Each item maps to the control row(s) it satisfies.

### Engineering-managed evidence (repo / CI artifacts)

| # | Evidence item | Source | Repo path / artifact | Controls | Owner | Ready by |
| --- | --- | --- | --- | --- | --- | --- |
| E01 | Branch protection + CODEOWNERS config | GitHub repo settings | `docs/branch-protection.md` + GH UI export | CC5.1, CC5.3, CC8.1 | Eng | 2026-05-23 |
| E02 | CI green-run history (90 days) | GitHub Actions | Actions API: runs on `main` per quarter | CC8.1, CC8.2 | Eng | 2026-07-04 |
| E03 | Filesystem vuln scan (trivy, blocking HIGH+) | CI `security` job | `.github/workflows/ci.yml` trivy step | CC7.1 | Eng | 2026-05-23 |
| E04 | SCA gate (snyk) | CI `security` job | `.github/workflows/ci.yml` snyk step | CC7.1, CC7.2 | Eng | 2026-05-23 |
| E05 | Secrets-scanning gate (gitleaks) | CI `security` job | `.github/workflows/ci.yml` gitleaks step + `.gitleaks.toml` | CC6.1, CC7.1 | Eng | 2026-05-23 |
| E06 | SBOM (CycloneDX 1.5 JSON) | CI `security` job | artifact `sbom-cyclonedx` | CC7.1, CC7.2, CC9.1 | Eng | 2026-05-23 |
| E07 | Threat model + security policy | Engineering | `loop_implementation/engineering/SECURITY.md` (git log shows review cadence) | CC2.1, CC3.2 | Security Eng | 2026-06-06 |
| E08 | Incident-response runbook | Engineering | `loop_implementation/engineering/RUNBOOKS.md` | CC2.2, CC7.4 | Security Eng | 2026-06-06 |
| E09 | DR runbook + drill log | Engineering (S572–S574) | `loop_implementation/engineering/DR.md` + drill scripts | CC7.5 | Eng | 2026-07-04 |
| E10 | Audit-trail completeness matrix | Engineering (S581) | `loop_implementation/engineering/AUDIT_COMPLETENESS.md` | CC4.1, CC6.5 | Security Eng | 2026-05-23 |
| E11 | Pen-test scope + RoE | Engineering (S576) | `loop_implementation/engineering/PEN_TEST.md` | CC6.2 | Security Eng | 2026-07-04 |
| E12 | Tenant data segregation (RLS DDL + tests) | Engineering | `data/SCHEMA.md` §RLS + test run | CC6.7 | Eng | 2026-05-23 |
| E13 | Encryption-at-rest + in-transit config | Helm + cloud KMS | `infra/helm/loop/values.yaml` + cloud KMS export | CC6.6 | Eng | 2026-05-23 |
| E14 | Pen-test report (Q2 2026) | External vendor | `s3://loop-pentest-archive/2026-q2/` (out-of-band PDF) | CC6.2 | Security Eng | 2026-07-04 |

### People / IT / Legal evidence (out-of-repo, owner-driven)

| # | Evidence item | Source | Controls | Owner | Ready by |
| --- | --- | --- | --- | --- | --- |
| P01 | Code of conduct signed (all staff) | HRIS attestations | CC1.1 | People | 2026-06-06 |
| P02 | Security awareness training completion records | Vanta training module | CC1.2 | People | 2026-06-13 |
| P03 | Background check reports (all production-access staff) | Checkr reports | CC1.4 | People | 2026-06-06 |
| P04 | Org chart (current) | HRIS export | CC1.3 | People | 2026-06-06 |
| P05 | IdP SSO + MFA policy export | Okta / Google Workspace | CC6.1 | IT | 2026-05-23 |
| P06 | Onboarding/offboarding workflows (last 12 months) | HRIS-driven IdP provisioning | CC6.3 | People + IT | 2026-06-06 |
| P07 | Endpoint MDM compliance report | Kandji / Jamf / Intune | CC6.4, CC6.8 | IT | 2026-05-23 |
| P08 | Production IAM export (least-privilege review) | Cloud provider IAM | CC6.2, CC6.5 | Eng | 2026-06-20 |
| P09 | Subprocessor DPA list | Legal | CC9.1 | Legal | 2026-06-20 |
| P10 | Vendor risk-tier review | Vanta vendor module | CC9.2 | Security Eng | 2026-06-20 |
| P11 | Production deploy approval records (last 90 days) | GH Actions environment protection rules | CC5.2 | Eng | 2026-07-04 |
| P12 | Management assertion (signed by CEO) | CEO | All families | CEO | 2026-07-28 |

## Change log

| Date       | Author       | Change                                         |
| ---------- | ------------ | ---------------------------------------------- |
| 2026-04-30 | GitHub Copilot (S046) | Initial kickoff tracker for Type 1.   |
| 2026-05-01 | copilot-titan (S571) | Added "Evidence sources index" mapping each CI gate / repo file → controls satisfied → auditor pull pattern; flipped CC7.1 to done; CC8.2 evidence pointer made concrete. |
| 2026-05-02 | copilot-thor (S582) | Kickoff meeting record added (§Kickoff meeting); evidence list finalised (§Evidence list — Type 1 pack); audit window dates committed (§Audit window & key dates); Vanta integration items and key milestones updated to reflect kickoff completion. |
