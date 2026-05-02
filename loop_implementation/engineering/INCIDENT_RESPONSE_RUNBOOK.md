# Loop — Incident Response Runbook

**Version:** 1.0 | **Owner:** Incident commander (rotating on-call) | **Last reviewed:** 2026-06-01
**Status:** Active — first game-day held 2026-06-01; see [GAME_DAY_LOG.md](GAME_DAY_LOG.md)

> **Quick-start:** Incident declared? Jump straight to [§3 Immediate actions](#3-immediate-actions).

---

## 1. Purpose and scope

This runbook governs how Loop Engineering responds to production incidents from initial
detection through resolution and post-incident review (PIR). It complements:

- `SECURITY.md §10` — severity levels, SLAs, customer notification obligations.
- `RUNBOOKS.md` — per-component runbooks (Postgres, Redis, Vault, etc.).
- `DR.md` — disaster-recovery scenarios requiring regional failover.

**In scope:** Any event that causes or risks causing degraded service, data exposure, or
policy violation in the Loop production environment.

---

## 2. Roles

| Role | Responsibility | Escalation |
|------|----------------|-----------|
| **Incident commander (IC)** | Declares incident; drives the response timeline; makes go/no-go decisions. | If no ack in 50 % of SLA window, auto-escalates to backup on-call. |
| **Tech lead** | Owns diagnosis and fix; coordinates with module owners; approves rollbacks. | IC can override and assign a different tech lead at any time. |
| **Comms lead** | Drafts customer-facing communications; manages status page; escalates to CEO for SEV1. | CEO is mandatory Comms lead for SEV1. |
| **Scribe** | Records timeline in the incident Slack channel: timestamps, decisions, commands run. | Any engineer present who is not actively debugging. |
| **Module owner** | SME for the affected subsystem; paged as needed. | Listed in CODEOWNERS; fallback is CTO. |

---

## 3. Immediate actions

### 3.1 Detect and declare

1. Alert fires in PagerDuty or Slack `#alerts`. On-call engineer acknowledges within SLA:
   - SEV1: ≤ 5 min
   - SEV2: ≤ 15 min
   - SEV3: ≤ 1 h
2. Engineer declares incident by running:
   ```
   /incident declare --severity SEV<N> --title "<short description>"
   ```
   This creates `#inc-YYYYMMDD-<slug>` in Slack and pages the IC rotation.

3. IC joins the channel and assigns roles (comms lead, scribe, tech lead).

### 3.2 Status page update

| Severity | Deadline | Template |
|----------|----------|----------|
| SEV1 | 15 min from declaration | "We are investigating reports of [impact]." |
| SEV2 | 30 min | Same |
| SEV3 | 2 h | Post only if customer-visible |

Status-page command:
```bash
loopctl statuspage update \
  --severity SEV1 \
  --title "Investigating [service] degradation" \
  --body "We are investigating an issue affecting [component]. Updates every 30 min."
```

---

## 4. Diagnosis checklist

Run in order; stop and act as soon as a root cause is identified.

### 4.1 Service health

```bash
# Control-plane pod status
kubectl -n loop-control get pods -o wide

# Data-plane pod status
kubectl -n loop-data get pods -o wide

# Recent error logs (last 10 min)
stern -n loop-control cp-api --since 10m | grep -i "error\|fatal\|panic"
stern -n loop-data dp-runtime --since 10m | grep -i "error\|fatal\|panic"
```

### 4.2 Database health

```bash
# Postgres primary
kubectl -n loop-data exec postgres-primary-0 -- pg_isready
kubectl -n loop-data exec postgres-primary-0 -- psql -U loop -c "SELECT now(), pg_is_in_recovery();"

# Redis
kubectl -n loop-data exec redis-master-0 -- redis-cli ping

# Qdrant
kubectl -n loop-data exec qdrant-0 -- curl -s localhost:6333/healthz
```

### 4.3 Dependency health

```bash
# Check outbound LLM provider latency
loopctl gateway status --all-providers

# Check NATS cluster
nats server report jetstream --server nats://nats-headless:4222
```

### 4.4 Recent deploys

```bash
# Last 3 deploys to production
kubectl -n loop-control rollout history deployment/cp-api
kubectl -n loop-data rollout history deployment/dp-runtime
```

---

## 5. Mitigation playbooks

### 5.1 Rollback a bad deploy

```bash
# Identify the last-good revision
kubectl -n loop-control rollout history deployment/cp-api

# Roll back
kubectl -n loop-control rollout undo deployment/cp-api --to-revision=<N>
kubectl -n loop-data rollout undo deployment/dp-runtime --to-revision=<N>

# Verify rollback completed
kubectl -n loop-control rollout status deployment/cp-api
```

### 5.2 Circuit-break a misbehaving LLM provider

```bash
loopctl gateway circuit-break --provider <name> --duration 30m
```

### 5.3 Pause a suspicious workspace (potential data-leak SEV1)

```bash
loopctl workspace pause --id <workspace-id> --reason "SEV1 investigation"
# Notify CTO + CEO immediately if cross-tenant leak confirmed
```

### 5.4 Rotate a compromised API key

```bash
loopctl api-key revoke --key-id <id> --reason "SEV1: suspected compromise"
```

---

## 6. Escalation matrix

| Condition | Action |
|-----------|--------|
| No IC ack after 50 % of SLA | PagerDuty auto-pages backup on-call |
| Cross-tenant data leak (any severity) | Page CTO + CEO within 5 min; treat as SEV1 |
| RCE in runtime sandbox | Page CTO + CISO within 5 min; isolate region |
| SLA breach imminent | IC can declare severity escalation unilaterally |
| GDPR notification needed | Comms lead notifies CTO; 72-h clock starts at detection |

---

## 7. Resolution and handoff

1. Root cause confirmed and mitigation applied.
2. Tech lead runs verification: key metrics back to SLO, error rate < 0.1 %.
3. IC declares incident resolved:
   ```
   /incident resolve --id <inc-id>
   ```
4. Status page updated to "Resolved".
5. Scribe posts final timeline summary in channel.
6. IC schedules PIR within 48 h.

---

## 8. Post-incident review (PIR)

**Mandatory for SEV1 and SEV2.** Optional (but encouraged) for SEV3.

PIR template:

```markdown
## PIR — <incident slug>

**Date:** YYYY-MM-DD  
**Severity:** SEV<N>  
**Duration:** HH:MM  
**Participants:** [list]

### Timeline
| Time (UTC) | Event |
|------------|-------|
| HH:MM | Alert fired |
| ... | ... |

### Root cause
[Clear, one-paragraph description]

### Contributing factors
- ...

### What went well
- ...

### What could be improved
- ...

### Action items
| # | Description | Owner | Due |
|---|-------------|-------|-----|
| 1 | ... | @eng | YYYY-MM-DD |
```

PIRs are stored in `loop_implementation/engineering/pirs/` and linked from the incident Slack channel.

---

## 9. Game-day cadence

Game-days are scheduled monthly by the IC rotation lead. Each session:

1. **Scope:** Pick one runbook (or a new failure scenario not covered by any runbook).
2. **Pre-read:** Participants read the relevant runbook 24 h in advance.
3. **Execution:** Red team injects the failure in staging; blue team responds per runbook.
4. **Debrief:** ≤ 30-min retro; gaps documented in `GAME_DAY_LOG.md`.
5. **Gaps tracked:** Each gap becomes a Linear ticket tagged `game-day-gap`; owner + due date required.

Game-day log: [GAME_DAY_LOG.md](GAME_DAY_LOG.md)

---

## 10. References

- `SECURITY.md §10` — severity SLAs and customer notification obligations
- `RUNBOOKS.md` — per-component runbooks
- `DR.md` — disaster recovery
- `SOC2.md` — audit evidence requirements (PIRs count as evidence)
- `PERFORMANCE.md` — SLO definitions used during incident triage
