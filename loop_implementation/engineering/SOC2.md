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
| CC7.1 | Vulnerability scanning on every PR                 | Eng         | CI logs                                        | partial |
| CC7.2 | Critical CVEs remediated within SLA                | Eng         | Vanta vuln tracker                             | ☐      |
| CC7.3 | 24/7 on-call rotation                              | Eng         | PagerDuty schedule                             | partial |
| CC7.4 | Incident post-mortems, blameless                   | Eng         | RUNBOOKS.md template                           | partial |
| CC7.5 | Backup + restore tested quarterly                  | Eng         | DR.md drill log                                | partial |

### CC8 — Change management

| ID    | Control                                            | Owner       | Evidence                                       | Status |
| ----- | -------------------------------------------------- | ----------- | ---------------------------------------------- | ------ |
| CC8.1 | All code changes via PR with peer review           | Eng         | GitHub PR history                              | done   |
| CC8.2 | Automated tests pass before merge                  | Eng         | CI status checks                               | done   |
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
