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
| All Vanta integrations live                | Week 2       | ☐       |
| Policy set published internally            | Week 3       | ☐       |
| Security training pushed to all staff      | Week 4       | ☐       |
| First control gap closed (CC6.x suite)     | Week 6       | ☐       |
| Auditor selected and engaged               | Week 6       | ☐       |
| Internal pre-audit walkthrough             | Week 9       | ☐       |
| Type 1 audit fieldwork                     | Week 10–11   | ☐       |
| Type 1 report issued                       | End of Q3    | ☐       |
| Type 2 observation window opens            | Day after T1 | ☐       |

## Out-of-scope clarifications

* **HIPAA / BAA** is *not* in scope for this audit. HIPAA-track work
  is sequenced after Type 2 issuance.
* **FedRAMP** is *not* in scope. Tracked on a separate program.
* **PCI** is *not* applicable; Loop never handles cardholder data.

## Change log

| Date       | Author       | Change                                         |
| ---------- | ------------ | ---------------------------------------------- |
| 2026-04-30 | GitHub Copilot (S046) | Initial kickoff tracker for Type 1.   |
| 2026-05-01 | copilot-titan (S571) | Added "Evidence sources index" mapping each CI gate / repo file → controls satisfied → auditor pull pattern; flipped CC7.1 to done; CC8.2 evidence pointer made concrete. |
