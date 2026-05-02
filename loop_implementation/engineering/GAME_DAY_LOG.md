# Loop — Game-Day Log

**Purpose:** Record every game-day session, outcomes, and tracked gaps.
**Cadence:** Monthly (last business day of each month preferred).
**Owner:** IC rotation lead.

See [INCIDENT_RESPONSE_RUNBOOK.md §9](INCIDENT_RESPONSE_RUNBOOK.md#9-game-day-cadence) for the game-day process.

---

## Game-day session log

| # | Date | Runbook / Scenario | Participants | Outcome | Gaps found | Gap tickets |
|---|------|--------------------|--------------|---------|------------|-------------|
| GD-001 | 2026-06-01 | RB-001 Postgres primary failover | Eng#1, Eng#2, IC-on-call | Pass — failover completed within RTO (4 min 12 s) | Alertmanager webhook to Slack delayed ~90 s; loopctl status command not in runbook PATH | LOOP-4210, LOOP-4211 |

---

## Gap tracker

| Gap ID | Description | Source session | Owner | Due | Status |
|--------|-------------|----------------|-------|-----|--------|
| LOOP-4210 | Alertmanager Slack webhook latency exceeds 60 s — investigate routing | GD-001 | Eng#2 | 2026-06-15 | Open |
| LOOP-4211 | Add `loopctl` to default PATH in all engineer dev environments; document in HANDBOOK | GD-001 | Eng#1 | 2026-06-10 | Open |

---

## Scheduling

Next session: **2026-07-01** — Scenario: RB-006 Tool sandbox compromise (Falco alert response)
Session lead: IC rotation lead (see on-call schedule)

---

## How to add a session record

1. Add a row to the **Game-day session log** table above.
2. Add each gap as a row in the **Gap tracker** table; create the Linear ticket first.
3. Commit and open a PR tagged `game-day`.
4. Close gap tickets when resolved; update the Status column here.
