# Bug Bounty Program -- Internal Operations Guide

## Overview

This document covers how the Loop security team operates the HackerOne
bug-bounty program day-to-day.  The public-facing policy is at
`docs/site/bug-bounty.md`.

## Roles

| Role | Responsibility |
|---|---|
| Bug-bounty coordinator | Primary HackerOne triage inbox; initial acknowledgement within 24 h |
| Security engineer | Technical triage; CVSS scoring; fix ownership assignment |
| Engineering manager | Escalation for Critical/High; communication with reporters |

## Triage SLA (internal)

Reports must reach a triage decision within **5 business days**:

* **Valid** -- assign CVSS, link to internal Jira, assign fix owner
* **Duplicate** -- link to the canonical report, close with explanation
* **Out of scope** -- close with explanation; suggest responsible-disclosure
  email if the issue is real but out of scope
* **Informational** -- close with educational note; no bounty
* **N/A** -- close with detailed explanation

## First-3-reports checklist

When the program launches, the security team must triage and close the first
three submitted reports before the program is considered "live" for KPIs:

- [ ] Report 1 acknowledged < 24 h, triage decision < 5 bd
- [ ] Report 2 acknowledged < 24 h, triage decision < 5 bd
- [ ] Report 3 acknowledged < 24 h, triage decision < 5 bd

Record outcomes in the triage log below.

## Triage log (first 3 reports)

| # | HackerOne ID | Submitted | Acknowledged | Decision | Severity | Bounty |
|---|---|---|---|---|---|---|
| 1 | H1-PENDING | -- | -- | -- | -- | -- |
| 2 | H1-PENDING | -- | -- | -- | -- | -- |
| 3 | H1-PENDING | -- | -- | -- | -- | -- |

## Fix ownership matrix

| Severity | Fix owner | Deadline |
|---|---|---|
| Critical | On-call security engineer (PagerDuty) | 14 calendar days |
| High | Assigned engineer + security review | 30 calendar days |
| Medium | Assigned engineer | 90 calendar days |
| Low | Backlog; milestone as available | 90 calendar days |

## Bounty payment process

1. Security engineer marks report **Resolved** on HackerOne.
2. Bug-bounty coordinator submits payment request to Finance within 5 bd.
3. HackerOne processes payment within 14 days of fix.
4. Finance confirms payment and coordinator closes the bounty record.

## Metrics (reviewed monthly)

* Mean time to acknowledge (MTTA) -- target < 24 h
* Mean time to triage (MTTT) -- target < 5 bd
* Mean time to resolve (MTTR by severity) -- see SLA above
* Bounty paid YTD
* Reports by severity distribution

## References

* Public policy: `docs/site/bug-bounty.md`
* SECURITY.md disclosure instructions: `loop_implementation/engineering/SECURITY.md`
* Incident response: `loop_implementation/engineering/INCIDENT_RESPONSE_RUNBOOK.md`
* HackerOne program settings: internal wiki (link TBD)
