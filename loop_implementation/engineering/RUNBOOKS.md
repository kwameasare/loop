# Loop — Operational Runbooks

**Status:** v0.1  •  **Owners:** primary on-call, with module owners as named below.
**Companion:** `engineering/SECURITY.md` (incident response process), `engineering/DR.md` (disaster recovery), `engineering/PERFORMANCE.md`.

Runbooks are stepwise, copy-pasteable, low-cognitive-load procedures for the things that go wrong. Every runbook has an owner, a known-good last-tested date, and a SEV target.

This file is the index. Per-runbook detail follows.

---

## 0. Runbook index

| ID | Title | Owner | Last drilled | SEV target |
|----|-------|-------|--------------|-----------|
| RB-001 | Postgres primary failover | Eng #2 | TBD M2 | SEV1, RTO ≤ 5 min |
| RB-002 | Redis cluster partition | Eng #2 | TBD M2 | SEV2, RTO ≤ 10 min |
| RB-003 | Qdrant unavailable | Eng #4 | TBD M3 | SEV2, RTO ≤ 15 min |
| RB-004 | NATS partition / cluster split | Eng #2 | TBD M3 | SEV2, RTO ≤ 10 min |
| RB-005 | LLM provider 5xx storm | Eng #1 | TBD M4 | SEV2, mitigated by gateway fallback |
| RB-006 | Tool sandbox compromise | Sec eng | TBD M5 | SEV1 — see Incident Response |
| RB-007 | Workspace cost runaway | Eng #1 | TBD M3 | SEV3 → escalate to SEV2 if customer-impacting |
| RB-008 | DSAR (Data Subject Access Request) export | Sec eng | TBD M4 | SEV3, deadline 30 days |
| RB-009 | Customer key rotation (BYOK) | Sec eng | M12 | SEV3, scheduled |
| RB-010 | Region cutover (cross-cloud migration) | Eng #2 | TBD M11 | SEV3, scheduled — multi-day playbook |
| RB-011 | Cassette refresh (eval) | Eng #4 | monthly | SEV3 |
| RB-012 | Voice POP outage | Eng #3 | TBD M6 | SEV2, route to alternate POP |
| RB-013 | Deploy controller stuck | Eng #2 | TBD M3 | SEV2 |
| RB-014 | Audit log chain integrity check | Sec eng | quarterly | SEV1 if mismatch found |
| RB-015 | Cross-tenant data-leak suspicion | Sec eng | TBD M5 | SEV1 — mandatory page CTO + CEO |
| RB-016 | Vault unsealed required | Eng #2 | TBD M2 | SEV1, blocks all secret reads |
| RB-017 | Channel provider credential revoked | Eng #7 | TBD M5 | SEV2 per affected channel |
| RB-018 | Mass deploy rollback | Eng #2 | TBD M4 | SEV1 — see process |
| RB-019 | Hire onboarding (Day 1 access) | CTO | weekly during hiring | SEV3 |
| RB-020 | Compromised API key | Sec eng | TBD M4 | SEV1 |
| RB-021 | Postgres PITR restore drill | Eng #2 | 2026-04-30 (synthetic) | SEV1, RTO ≤ 60 min, RPO ≤ 5 min |

Drill cadence: every runbook drilled once before its first prod-incident; every active runbook re-drilled at least every 6 months. Drill results captured in this file.

---

## RB-001 — Postgres primary failover

**Owner:** Eng #2.  **SEV target:** SEV1, RTO ≤ 5 min, RPO ≤ 30 s.

**Symptoms:** API returns `LOOP-API-501` cluster-wide; `dp-runtime` logs show connection refused / dead connection; PagerDuty alert "postgres primary down."

### Steps

1. **Acknowledge** the page within 5 min. Open `#inc-YYYYMMDD-pg-failover`.
2. **Check Postgres status** in the affected region:
   ```bash
   kubectl -n loop-data get pods -l app=postgres -o wide
   kubectl -n loop-data exec postgres-primary-0 -- pg_isready
   ```
3. **Verify automated failover triggered** (Patroni / managed Postgres failover):
   - Cloud-managed: failover happens automatically via the cloud's HA feature; check provider console.
   - Self-host (Patroni): `kubectl -n loop-data exec patroni-0 -- patronictl list`. The new primary should show as `Leader`.
4. **If automated failover did NOT trigger** within 60 s:
   - Force failover: `patronictl failover --master postgres-primary-0 --candidate postgres-replica-0`.
   - For cloud-managed: trigger the provider's failover API (use the runbook attachment per cloud).
5. **Update connection pool** (PgBouncer):
   ```bash
   kubectl -n loop-data rollout restart statefulset/pgbouncer
   ```
   Wait for `kubectl rollout status` to clear. Pods should reconnect to the new primary.
6. **Verify recovery:**
   - `curl https://api.<region>.loop.example/v1/healthz` should return 200.
   - `dp-runtime` error rate in Grafana should fall below 1%.
   - Tail `dp-runtime` logs for "connection established" entries.
7. **Status page** update: post recovery message.
8. **Post-incident review** within 48 h — see `engineering/SECURITY.md` §10. Capture: root cause, time-to-detect, time-to-mitigate, action items.

### Recent drills

_(none yet — first drill scheduled M2 W2)_

### Anti-patterns

- ❌ Manually point apps at the replica with stale credentials. Always go through PgBouncer.
- ❌ Skip step 5; pool will hold dead connections for up to 30 min.

---

## RB-002 — Redis cluster partition

**Owner:** Eng #2.  **SEV target:** SEV2, RTO ≤ 10 min.

**Symptoms:** session-memory reads time out; LLM gateway cache miss rate spikes; rate-limit counters return inconsistent values.

### Steps

1. Acknowledge page. Open incident channel.
2. Identify affected shards: `kubectl -n loop-data exec redis-cluster-0 -- redis-cli cluster nodes`.
3. If a minority of shards is unavailable, requests routed to surviving shards. Monitor for cascading slowness.
4. If majority unavailable:
   - Sessions degrade to "no session memory" (correct behavior; turn-fresh agents).
   - Gateway cache misses; expect cost spike. Raise an alert to the workspace owners >$X/hr cost-impacted.
5. Repair partition:
   - Self-host: `kubectl -n loop-data delete pod <down-pod>`; sentinel will reform.
   - Managed: trigger provider failover.
6. Validate: `redis-cli ping`; runtime cache hit rate recovers in ~5 min.
7. PIR: capture data loss (session memory expired during outage cannot be recovered — that is by design, but document scale).

---

## RB-005 — LLM provider 5xx storm

**Owner:** Eng #1.  **SEV target:** SEV2 (auto-mitigated by gateway).

**Symptoms:** Anthropic / OpenAI / etc. returns 5xx > 5% over 60 s; gateway alert fires.

### Steps

1. Acknowledge page.
2. Verify provider status: check provider's status page (Anthropic, OpenAI, Bedrock, etc.).
3. Gateway should already be falling back to secondary provider via model alias resolution. Verify in Grafana: `loop_gateway_provider_dispatch_total` should show traffic shifting.
4. If fallback is NOT engaging:
   - Check `LOOP_GATEWAY_FALLBACK_MODEL` is configured.
   - Manually flip: `kubectl -n loop-data set env deploy/dp-gateway LOOP_GATEWAY_FORCE_FALLBACK=true`.
5. Notify customers via status page if degradation > 30 min.
6. When provider recovers, remove force flag; gateway resumes primary routing.

---

## RB-006 — Tool sandbox compromise

**Owner:** Sec eng.  **SEV target:** SEV1.

**Symptoms:** alert from sandbox supervisor about kernel call from inside the VM; Firecracker `panic` log; egress to disallowed IP detected.

### Steps

1. **Page CTO + CEO immediately.** This is mandatory for any suspected sandbox escape.
2. **Quarantine** the affected sandbox node:
   ```bash
   kubectl cordon <node>
   kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
   ```
3. **Capture forensic data** before deletion:
   - Snapshot Firecracker rootfs.
   - Dump in-flight network connections (`conntrack -L`).
   - Save NATS event history for the affected workspace.
4. **Disable** the suspect tool / MCP server across affected workspaces:
   ```bash
   loop admin mcp-server disable --workspace=<ws> --server=<server>
   ```
5. Run audit-log chain check (RB-014) to detect tampering.
6. **External notification** if customer data may have been exposed: 72 h GDPR window starts now.
7. PIR within 24 h. Public CVE if relevant.

---

## RB-007 — Workspace cost runaway

**Owner:** Eng #1.  **SEV target:** SEV3 unless customer-impacted.

**Symptoms:** `loop_workspace_cost_usd` > 5× rolling 24 h baseline; budget cap close to limit but not yet hit.

### Steps

1. Identify the workspace + cause:
   ```bash
   loop admin usage --workspace=<id> --groupby=agent --since=24h
   ```
2. If a specific agent is the cause, check for runaway loop:
   - Trace tail: `loop admin tail --agent=<id>`.
   - Look for repeated tool calls or many iterations per turn.
3. Notify customer (status page + email + Slack if connector exists).
4. **Soft action** first: lower the agent's hard cap so future turns degrade.
5. **Hard action** if needed: pause the agent (`loop admin agent pause <id>`).
6. PIR: was this a customer bug, a runaway, or a malicious abuse?

---

## RB-008 — DSAR (Data Subject Access Request) export

**Owner:** Sec eng.  **SEV target:** SEV3, deadline 30 days from request receipt.

**Steps:**

1. Validate request authenticity (signed by workspace admin / explicit end-user proof of identity).
2. File request in `data_export_requests` table.
3. Run export:
   ```bash
   loop admin dsar export --workspace=<ws> --user=<user_id> --output=s3://exports/<ws>/<request_id>.tar.zst
   ```
4. Bundle includes:
   - Conversations (JSON per conversation, full content + metadata).
   - Memory (user, episodic — both narrative and embedding manifests).
   - Traces (OTLP per turn).
   - Channel-side identity link records.
5. Sign the bundle with the workspace KMS key.
6. Generate a 7-day-TTL presigned download URL.
7. Email link + checksum to the requesting customer admin.
8. Audit-log the export with actor, target, bytes, key prefix.

---

## RB-010 — Region cutover

**Owner:** Eng #2.  **SEV target:** SEV3, scheduled migration.

Multi-day playbook — see attached `engineering/runbooks/region-cutover.md` (TODO: split out for readability).

Summary:
1. Provision target environment via Terraform.
2. Replicate Postgres via logical replication to target.
3. Snapshot + restore Qdrant collections.
4. Replicate object storage (rclone).
5. Soak target environment with synthetic workspace load.
6. Cut over `region` field on the workspace; runtime in target picks up traffic.
7. Soak window 7 days; if green, decommission source.
8. Document incident-style PIR in this folder.

---

## RB-011 — Cassette refresh (eval)

**Owner:** Eng #4.  **SEV target:** SEV3, monthly cadence.

**When:** 1st of every month, or when a scorer rubric or prompt template changes.

**Steps:**

1. Pull latest `main`. Run `loop eval record <suite-name> --refresh-cassettes` per active suite.
2. Inspect the diff in `tests/fixtures/llm/<suite>.yaml`.
3. Review changes for:
   - Drift in expected behavior (acceptable; document).
   - Drift in scorer thresholds (raise team review).
   - New tools called (raise team review).
4. Open PR with the cassette delta + summary; require Eng #4 + the agent owner approval.
5. Merge; the refresh date is captured in the cassette header.

Cassettes ≥ 90 days old start failing eval gating; ≥ 30 days emit a warning.

---

## RB-014 — Audit log chain integrity check

**Owner:** Sec eng.  **SEV target:** SEV1 if mismatch.

**Cadence:** quarterly automated; on-demand on suspicion.

```bash
loop admin audit verify --workspace=<id_or_all> --since=<date>
```

If verification fails:
1. Page CTO + CEO immediately.
2. Suspend writes to audit log (write to a quarantine stream instead).
3. Forensic capture of the row hashes, control-plane Postgres binlog, and ClickHouse mirror.
4. Determine whether tampering was internal (operator with DB access — should not be possible per least-privilege) or external (compromise).
5. Disclose per RB-006 obligations.

---

## RB-018 — Mass deploy rollback

**Owner:** Eng #2.  **SEV target:** SEV1.

**When:** a regression makes it past eval gating into prod (e.g., partial traffic) and is causing customer-visible failures.

**Steps:**

1. Identify the offending agent version + rollout %.
2. Trigger rollback via cp-deploy-controller:
   ```bash
   loop admin deploy rollback --agent=<id> --target=<previous-version>
   ```
3. Verify all pods serve the rollback version: `kubectl rollout status deploy/dp-runtime`.
4. **Disable eval-gating override** until root cause is fixed:
   ```bash
   loop admin agent set --id=<id> --eval-gating-required=true
   ```
5. PIR within 24 h. Goal: figure out how the regression slipped past evals — usually a missing eval case. Add the missing case before re-deploying.

---

## RB-021 — Postgres PITR restore drill

**Owner:** Eng #2.  **SEV target:** SEV1, **RTO ≤ 60 min**, RPO ≤ 5 min.

**Companion:** `engineering/DR.md` §2 (backup strategy), `data/SCHEMA.md` (object-store layout), `scripts/dr_postgres_pitr_drill.sh` (drill driver).

**Purpose:** prove that WAL archived to the per-region S3-compatible bucket can be replayed to a recovery point of our choice and the cluster brought back to read-write within the published RTO. This drill is the SOC2 evidence pull for **CC7.5 / A1.2** ("backups are restorable") and the entitlement check for the **<1h RTO** SLO published on the status page.

**Scope:** Postgres logical cluster only. ClickHouse, Redis, Qdrant have their own runbooks (RB-002, RB-003, RB-007).

### Preconditions

- WAL-G archive bucket is reachable from the drill VPC (read-only IAM role).
- A staging Postgres cluster (`postgres-drill-${date}`) is provisionable in <5 min via the drill helm chart (`infra/helm/loop/values-drill.yaml`).
- The KMS data key for the workspace whose backup you are restoring is present in the drill region (cross-region replicated keys only; BYOK keys must be re-granted by the customer for cross-region drills).

### Steps (target wall-clock budgets)

| #  | Step                                                                 | Budget | Cumulative |
| -- | -------------------------------------------------------------------- | ------ | ---------- |
| 1  | Acknowledge drill kickoff in `#dr-drills`; record `T0` UTC.          | 1 min  | 1 min      |
| 2  | Pick a target recovery time (default: `now() - 15min`).              | 1 min  | 2 min      |
| 3  | Provision the drill cluster:<br>`./scripts/dr_postgres_pitr_drill.sh provision --region=<r> --rt=<iso8601>` | 5 min  | 7 min      |
| 4  | Drill driver fetches the latest base backup (`wal-g backup-fetch`).  | 8 min  | 15 min     |
| 5  | Drill driver replays WAL up to the target time (`wal-g wal-fetch` + Postgres recovery). | 25 min | 40 min     |
| 6  | Cluster reaches consistent state and accepts read-only traffic.      | 3 min  | 43 min     |
| 7  | Smoke checks: row counts on `workspaces`, `agents`, `turns`; SHA-256 of a sentinel row. | 4 min  | 47 min     |
| 8  | Promote to read-write (`pg_ctl promote`); confirm `pg_is_in_recovery() = false`. | 2 min  | 49 min     |
| 9  | Drill teardown: tear down the drill cluster, archive the driver log to `s3://loop-dr-evidence/<date>/`. | 5 min  | 54 min     |
| 10 | File the drill report row in this runbook §Recent drills.            | 1 min  | 55 min     |

**Total budget: 55 min — 5 min slack on the 60 min RTO.** Steps 4 and 5 dominate; if either exceeds 1.5× budget, abort the drill and open a SEV2 to investigate the archive (likely WAL gap or KMS throttling).

### Drill driver invocation

```bash
./scripts/dr_postgres_pitr_drill.sh \
  --region=us-east-1 \
  --workspace-id=ws_drill_synthetic \
  --rt=2026-04-30T12:00:00Z \
  --bucket=s3://loop-wal-archive-us-east-1
```

The driver writes a structured log to stdout (one JSON line per step) which the report-archival step uploads verbatim. Sample line:

```json
{"step": 5, "name": "wal-replay", "started_at": "…", "ended_at": "…", "duration_s": 1473, "ok": true}
```

### Recent drills

| Date       | Region        | Driver       | Wall-clock | Result    | Notes                                     |
| ---------- | ------------- | ------------ | ---------- | --------- | ----------------------------------------- |
| 2026-04-30 | us-east-1     | synthetic CI | 51 min     | ✅ pass    | WAL replay 23m11s; smoke checks all green. |

First real-region drill scheduled for the M3 hardening week; cadence thereafter is **monthly automated** (CI-driven against a synthetic workspace) and **quarterly manual** (engineer-on-call against a dormant production-like workspace).

### Anti-patterns

- ❌ Restoring into the live cluster's namespace. Always provision a `postgres-drill-*` namespace; the drill driver refuses if the target name does not match the prefix.
- ❌ Skipping step 9 teardown. Stale drill clusters cost ~$30/day and accumulate fast.
- ❌ Using a recovery target older than the PITR window (14 days standard / 90 days enterprise). The driver validates `--rt` against the bucket manifest before doing any work.
- ❌ Treating a green drill as a license to skip the next monthly run. Drift in WAL format and IAM policy is detected only by repeated runs.

### Evidence captured

For each drill, the following are uploaded to `s3://loop-dr-evidence/<date>/`:

- `driver.log` — full structured driver output.
- `step-timings.tsv` — one row per step with budget vs actual.
- `smoke.json` — row counts, sentinel hash.
- `cluster-events.txt` — `kubectl get events` from the drill namespace.

The Vanta evidence collector pulls `step-timings.tsv` weekly and asserts every row's `ok=true` (control CC7.5 / A1.2).

---

## How to add a new runbook

1. Pick the next free `RB-NNN` (use the index above; do not reuse retired numbers).
2. Add a row in §0.
3. Write the runbook section using this template (also lives at `engineering/templates/RUNBOOK_TEMPLATE.md`):
   - Owner + SEV target
   - Symptoms (concrete log lines / alert text)
   - Steps (numbered, copy-pasteable)
   - Recent drills
   - Anti-patterns
4. Drill it once before first prod use. Capture the drill date in the index row.
5. Re-drill every 6 months minimum.
