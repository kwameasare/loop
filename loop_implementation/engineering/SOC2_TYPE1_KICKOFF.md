# SOC2 Type 1 — attestation kickoff (S582)

**Owner:** Sec/Compliance Eng · **Last reviewed:** 2026-05-02 (copilot-titan, S582)

This document commits Loop to a specific SOC2 Type 1 audit window and
the evidence pack we will hand the auditor on day one of fieldwork. It
is the engineering-side artifact of the Type 1 attestation kickoff:
the actual kickoff meeting (auditor + Loop CEO + Sec/Compliance Eng
lead) is owned by Operations and is tracked separately in
`operations/SERIES_A.md`. Everything below is binding for engineering
once the kickoff meeting confirms the audit window.

## Audit framing

| Item               | Value                                                  |
|--------------------|--------------------------------------------------------|
| Framework          | SOC2 Type 1 (point-in-time)                            |
| Trust criteria     | Security, Availability, Confidentiality                |
| Snapshot date      | **2026-09-30** (90 days after sprint S30 close)        |
| Fieldwork window   | 2026-09-30 → 2026-10-31 (30-day evidence window)       |
| Report target      | 2026-12-15 (auditor SLA: 8 weeks post fieldwork)       |
| Scope — services   | control-plane, data-plane, runtime, gateway, voice, channels, kb-engine, eval-harness |
| Scope — environments | production (us-east-2, eu-west-1) + staging          |
| Out of scope       | Studio frontend (transitively in scope via cp-api), local-dev fixtures, `examples/*` reference apps |

The 90-day lead time is calibrated against the SOC2 Type 1 readiness
gates already shipped: branch protection (S119), CI security stack
(S578/S579/S580), control mapping (S571), audit-trail coverage matrix
(S581).

## Evidence pack (day-one delivery)

Maps to SOC2.md "Evidence sources index" (S571). Items below are
cross-references; the auditor pulls each item from the `Repo path /
artifact` column of that index plus the supplemental items in §Vanta
integration checklist.

### Engineering-managed evidence (auto-pull)

| # | Evidence                                | Source                                               | Controls satisfied   |
|---|-----------------------------------------|------------------------------------------------------|----------------------|
| 1 | Branch protection config screenshot      | GitHub repo settings → branches (admin export)       | CC5.1, CC5.3, CC8.1  |
| 2 | CI green-status history (90 days)        | GitHub Actions runs, exported via `gh run list`      | CC8.1, CC8.2         |
| 3 | Trivy fs scan results                    | `.github/workflows/ci.yml` `security` job (S579)     | CC7.1                |
| 4 | Snyk SCA results                         | Snyk dashboard + `security` job (S579)               | CC7.1, CC7.2         |
| 5 | Gitleaks secrets scan results            | `security` job (S580) + `.gitleaks.toml`             | CC6.1, CC7.1         |
| 6 | CycloneDX SBOM per release               | `sbom-cyclonedx` GH artifact (S578) — produced by `.github/workflows/ci.yml` | CC7.1, CC7.2, CC9.1  |
| 7 | Audit-trail coverage matrix              | `loop_implementation/engineering/AUDIT_COVERAGE.md` (S581) | CC4.1                |
| 8 | Threat model + STRIDE                    | `loop_implementation/engineering/SECURITY.md` §2     | CC3.2                |
| 9 | Encryption at rest config                | `loop_implementation/engineering/SECURITY.md` §4.1 + KMS deploy state | CC6.6   |
| 10| Tenant isolation tests                   | `packages/control-plane/_tests/test_workspace_region_pinning.py` + RLS tests | CC6.7   |
| 11| Cross-region telemetry filter            | `packages/sdk-py/loop/observability/region_filter.py` (S596) | CC6.7        |
| 12| Incident response runbook                | `loop_implementation/engineering/RUNBOOKS.md`        | CC2.2, CC7.4         |
| 13| DR runbook + RTO/RPO measurements        | `loop_implementation/engineering/DR.md` (S575 — pending) | CC7.5            |

### Operations-managed evidence (auditor pulls from Ops)

| # | Evidence                                | Owner    | Notes                                            |
|---|-----------------------------------------|----------|--------------------------------------------------|
| 14| Vendor risk assessments                 | Ops      | Vanta vendor module                              |
| 15| Background check completion             | HR/Ops   | One per FTE                                      |
| 16| Security training records (annual)      | HR/Ops   | One per FTE                                      |
| 17| Acceptable Use Policy + ack             | HR/Ops   | One per FTE                                      |
| 18| Access reviews (quarterly)              | Ops      | Last 4 quarters at snapshot                      |
| 19| Termination access-revocation log       | Ops      | Per termination                                  |
| 20| Change management ticket sample (n=25)  | Ops      | Maps GitHub PRs ↔ Linear tickets                 |

## Kickoff agenda (60 minutes, owned by Ops)

1. Auditor introductions + SoW review (10 min)
2. Confirm framework, criteria, scope, and snapshot date — sign off
   on the table at the top of this doc (15 min)
3. Walk through engineering-managed evidence (#1–#13) using the
   AUDIT_COVERAGE / SECURITY Evidence sources index — confirm
   auditor portal access (15 min)
4. Walk through operations-managed evidence (#14–#20) — confirm
   ownership and target dates (10 min)
5. Confirm communication cadence (weekly status, SLA on questions),
   confidentiality terms, and report-distribution list (10 min)

## Pre-kickoff prerequisites (engineering — owned by us)

- [x] Control mapping doc (`SOC2.md`) with Evidence sources index — S571
- [x] CI security stack landed (trivy + snyk + gitleaks + SBOM) — S578/S579/S580
- [x] Audit-trail coverage matrix — S581
- [x] Cross-region PII filter — S596
- [ ] DR runbook with measured RTO/RPO — S575 (pending; titan queue)
- [ ] Pen-test scope + RoE doc — S576 (pending; thor queue)
- [ ] Pen-test fix queue tracked — S577 (pending; thor queue)

When the four open boxes flip green the engineering bar is clear.

## Post-kickoff commitments

Within five business days of the actual kickoff meeting, this doc is
amended in a follow-up PR to record:

- **Auditor firm + lead partner name**
- **Signed engagement letter date**
- **Confirmed snapshot date** (may differ from the proposed
  `2026-09-30` if scoping changes)
- **Auditor portal URL** (for evidence drop)

Until those four items land, the meeting itself is a human follow-up
tracked in `operations/SERIES_A.md` § "SOC2 Type 1 milestones". The
kickoff blocker is operational, not engineering.

## Status

| Field                         | Value                                |
|-------------------------------|--------------------------------------|
| Engineering prep              | ready (all hard-gated items shipped) |
| Operations engagement         | pending (Ops to schedule)            |
| Auditor selection             | pending (Ops shortlist by 2026-06-15)|
| Audit window committed (eng)  | yes — 2026-09-30 ± 0 days            |
| Evidence pack scope committed | yes — 20 items above                 |
