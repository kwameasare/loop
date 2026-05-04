# Loop — Operational Runbooks

**Status:** v0.1  •  **Owners:** primary on-call, with module owners as named below.
**Companion:** `engineering/SECURITY.md` (incident response process), `engineering/DR.md` (disaster recovery), `engineering/PERFORMANCE.md`.

Runbooks are stepwise, copy-pasteable, low-cognitive-load procedures for the things that go wrong. Every runbook has an owner, a known-good last-tested date, and a SEV target.

This file is the index. Per-runbook detail follows.

---

## 0. Runbook index

| ID | Title | Owner | Last drilled | SEV target |
|----|-------|-------|--------------|-----------|
| RB-001 | Postgres primary failover | Eng #2 | 2026-05-04 (synthetic) | SEV1, RTO ≤ 5 min |
| RB-002 | Redis cluster partition | Eng #2 | 2026-05-04 (synthetic) | SEV2, RTO ≤ 10 min |
| RB-003 | Qdrant unavailable | Eng #4 | 2026-05-04 (synthetic) | SEV2, RTO ≤ 15 min |
| RB-004 | NATS partition / cluster split | Eng #2 | 2026-05-04 (synthetic) | SEV2, RTO ≤ 10 min |
| RB-005 | LLM provider 5xx storm | Eng #1 | 2026-05-04 (synthetic) | SEV2, mitigated by gateway fallback |
| RB-006 | Tool sandbox compromise | Sec eng | 2026-05-04 (synthetic) | SEV1 — see Incident Response |
| RB-007 | Workspace cost runaway | Eng #1 | 2026-05-04 (synthetic) | SEV3 → escalate to SEV2 if customer-impacting |
| RB-008 | DSAR (Data Subject Access Request) export | Sec eng | 2026-05-04 (synthetic) | SEV3, deadline 30 days |
| RB-009 | Customer key rotation (BYOK) | Sec eng | M12 | SEV3, scheduled |
| RB-010 | Region cutover (cross-cloud migration) | Eng #2 | 2026-05-04 (synthetic) | SEV3, scheduled — multi-day playbook |
| RB-011 | Cassette refresh (eval) | Eng #4 | monthly | SEV3 |
| RB-012 | Voice POP outage | Eng #3 | 2026-05-04 (synthetic) | SEV2, route to alternate POP |
| RB-013 | Deploy controller stuck | Eng #2 | 2026-05-04 (synthetic) | SEV2 |
| RB-014 | Audit log chain integrity check | Sec eng | quarterly | SEV1 if mismatch found |
| RB-015 | Cross-tenant data-leak suspicion | Sec eng | 2026-05-04 (synthetic) | SEV1 — mandatory page CTO + CEO |
| RB-016 | Vault unsealed required | Eng #2 | 2026-05-04 (synthetic) | SEV1, blocks all secret reads |
| RB-017 | Channel provider credential revoked | Eng #7 | 2026-05-04 (synthetic) | SEV2 per affected channel |
| RB-018 | Mass deploy rollback | Eng #2 | 2026-05-04 (synthetic) | SEV1 — see process |
| RB-019 | Hire onboarding (Day 1 access) | CTO | weekly during hiring | SEV3 |
| RB-020 | Compromised API key | Sec eng | 2026-05-04 (synthetic) | SEV1 |
| RB-021 | Postgres PITR restore drill | Eng #2 | 2026-04-30 (synthetic) | SEV1, RTO ≤ 60 min, RPO ≤ 5 min |
| RB-022 | ClickHouse snapshot restore drill | Eng #4 | 2026-05-01 (synthetic) | SEV2, RTO ≤ 90 min, RPO ≤ 30 min |
| RB-023 | Object-store replication integrity failure | Eng #2 | 2026-05-02 (synthetic) | SEV2, RTO ≤ 30 min |
| RB-024 | BYO Vault credential rotation | Sec eng | 2026-05-04 (synthetic) | SEV2 if stale; SEV1 if leaked |

Drill cadence: every runbook drilled once before its first prod-incident; every active runbook re-drilled at least every 6 months. Drill results captured in this file.

---

## RB-001 — Postgres primary failover

**Owner:** Eng #2.  **SEV target:** SEV1, RTO ≤ 5 min, RPO ≤ 30 s.

**Symptoms / alert fire:** API returns `LOOP-API-501` cluster-wide; `dp-runtime` logs show connection refused / dead connection; PagerDuty alert "postgres primary down."

**First 5-minute triage:**

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

**Mitigation:** force failover when automation stalls and restart PgBouncer to flush dead connections.

**Recovery validation:**
- `pg_isready` passes on leader and app health endpoint returns 200.
- Runtime error rate returns to baseline.

### Recent drills

| Date       | Region    | Type      | Result | Notes |
| ---------- | --------- | --------- | ------ | ----- |
| 2026-05-04 | us-east-1 | synthetic | ✅ pass | failover + pool reconnect under 5 min |

**Drill cadence + last drilled date:** monthly synthetic failover; last drilled 2026-05-04.

### Anti-patterns

- ❌ Manually point apps at the replica with stale credentials. Always go through PgBouncer.
- ❌ Skip step 5; pool will hold dead connections for up to 30 min.

---

## RB-002 — Redis cluster partition

**Owner:** Eng #2.  **SEV target:** SEV2, RTO ≤ 10 min.

**Symptoms / alert fire:** session-memory reads time out; LLM gateway cache miss rate spikes; rate-limit counters return inconsistent values.

**First 5-minute triage:**

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

**Mitigation:** route traffic away from partitioned shards; restart failed members and force rejoin if quorum is lost.

**Recovery validation:**
- `redis-cli cluster info` reports `cluster_state:ok`.
- Cache-hit ratio and rate-limit consistency return to baseline.

**Drill cadence + last drilled date:** monthly synthetic failover drill; last drilled 2026-05-04.

---

## RB-003 — Qdrant unavailable

**Owner:** Eng #4.  **SEV target:** SEV2, RTO ≤ 15 min.

**Symptoms / alert fire:**
- Alert: `qdrant_up == 0` for 2 minutes.
- KB retrieval latency spikes; semantic search returns 5xx.

**First 5-minute triage:**
1. Confirm outage scope:
   ```bash
   kubectl -n loop-data get pods -l app.kubernetes.io/name=qdrant
   kubectl -n loop-data get svc loop-qdrant
   ```
2. Check health endpoint:
   ```bash
   kubectl -n loop-data port-forward svc/loop-qdrant 16333:6333 >/tmp/qdrant-pf.log 2>&1 &
   curl -fsS http://127.0.0.1:16333/healthz
   ```
3. Inspect recent failures in kb-engine logs:
   ```bash
   kubectl -n loop-data logs deploy/loop-loop-kb-engine --tail=120
   ```

**Mitigation:**
- If single pod issue, recycle pod and wait for index attach.
- If storage issue, fail over to managed Qdrant endpoint via `externals.qdrantUrl` and set `qdrant.enabled=false` on emergency upgrade.

**Recovery validation:**
- `/healthz` returns `ok`.
- `loop admin kb search` returns results for the canary document.
- `kb_engine_query_errors_total` returns to baseline.

**Drill cadence + last drilled date:** monthly synthetic outage simulation; last drilled 2026-05-04.

---

## RB-004 — NATS partition / cluster split

**Owner:** Eng #2.  **SEV target:** SEV2, RTO ≤ 10 min.

**Symptoms / alert fire:**
- Alert: `nats_jetstream_cluster_healthy == 0`.
- Event ingestion stalls; delayed tool results and webhook processing backlog.

**First 5-minute triage:**
1. Verify cluster state:
   ```bash
   kubectl -n loop-data exec deploy/loop-nats -- nats server report jetstream
   kubectl -n loop-data get pods -l app.kubernetes.io/name=nats
   ```
2. Inspect stream lag and consumers:
   ```bash
   kubectl -n loop-data exec deploy/loop-nats -- nats stream ls
   kubectl -n loop-data exec deploy/loop-nats -- nats consumer ls EVENTS
   ```
3. Check for node/network partition indicators in pod events.

**Mitigation:**
- Restart out-of-date followers first, then leader if necessary.
- If quorum cannot be restored quickly, route ingest to backup region queue and pause non-critical consumers.

**Recovery validation:**
- JetStream report returns healthy leader/follower state.
- Backlog drains and consumer lag falls below on-call threshold.

**Drill cadence + last drilled date:** monthly synthetic broker partition test; last drilled 2026-05-04.

---

## RB-005 — LLM provider 5xx storm

**Owner:** Eng #1.  **SEV target:** SEV2 (auto-mitigated by gateway).

**Symptoms / alert fire:** Anthropic / OpenAI / etc. returns 5xx > 5% over 60 seconds; gateway provider outage alert fires.

**First 5-minute triage:**
1. Acknowledge page and confirm provider health dashboard.
2. Verify live traffic shift in Grafana (`loop_gateway_provider_dispatch_total`).
3. Confirm fallback model configuration in gateway deployment.

**Mitigation:**
- If fallback did not engage automatically, enable forced fallback:
   ```bash
   kubectl -n loop-data set env deploy/dp-gateway LOOP_GATEWAY_FORCE_FALLBACK=true
   ```
- Notify customers via status page if degradation lasts over 30 minutes.

**Recovery validation:**
- Primary provider 5xx rate remains below 1% for 15 minutes.
- Remove forced flag and confirm normal routing split resumes.

**Drill cadence + last drilled date:** monthly provider-failover simulation; last drilled 2026-05-04.

---

## RB-006 — Tool sandbox compromise

**Owner:** Sec eng.  **SEV target:** SEV1.

**Symptoms / alert fire:** sandbox supervisor flags kernel-level escape attempt, Firecracker panic, or disallowed egress.

**First 5-minute triage:**
1. **Page CTO + CEO immediately** and open SEV1 bridge.
2. Quarantine impacted node:
   ```bash
   kubectl cordon <node>
   kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
   ```
3. Capture volatile artifacts (connections/process table/log tails).

**Mitigation:**
- Snapshot forensic evidence before deletion of compromised assets.
- Disable suspect tool/MCP server across impacted workspaces:
  ```bash
  loop admin mcp-server disable --workspace=<ws> --server=<server>
  ```
- Run RB-014 audit-chain verification and prepare regulatory disclosure if needed.

**Recovery validation:**
- No further compromised indicators across new sandbox sessions.
- Forensic timeline completed and containment verified by security lead.

**Drill cadence + last drilled date:** quarterly sandbox containment tabletop; last drilled 2026-05-04.

---

## RB-007 — Workspace cost runaway

**Owner:** Eng #1.  **SEV target:** SEV3 unless customer-impacted.

**Symptoms / alert fire:** `loop_workspace_cost_usd` exceeds 5x rolling 24-hour baseline; budget-cap alert near threshold.

**First 5-minute triage:**
1. Identify workspace and cost source:
   ```bash
   loop admin usage --workspace=<id> --groupby=agent --since=24h
   ```
2. Inspect likely runaway agents:
   ```bash
   loop admin tail --agent=<id>
   ```
3. Confirm whether customer impact is active.

**Mitigation:**
- Lower hard caps for offending agents.
- Pause agent if spend acceleration continues:
  ```bash
  loop admin agent pause <id>
  ```
- Notify customer with ETA and recommended temporary safeguards.

**Recovery validation:**
- Workspace spend returns below threshold trajectory.
- No runaway loop signatures in recent traces.

**Drill cadence + last drilled date:** monthly synthetic spend-runaway simulation; last drilled 2026-05-04.

---

## RB-008 — DSAR (Data Subject Access Request) export

**Owner:** Sec eng.  **SEV target:** SEV3, deadline 30 days from request receipt.

**Symptoms / alert fire:** new DSAR request opened or DSAR SLA breach warning triggers.

**First 5-minute triage:**
1. Validate request authenticity (workspace admin signature / identity proof).
2. Register request in `data_export_requests` and assign owner.
3. Confirm due date against legal SLA timer.

**Mitigation (execution):**
1. Run export:
   ```bash
   loop admin dsar export --workspace=<ws> --user=<user_id> --output=s3://exports/<ws>/<request_id>.tar.zst
   ```
2. Ensure bundle contains conversations, memory manifests, traces, and identity-link records.
3. Sign bundle with workspace KMS key and generate 7-day presigned URL.
4. Deliver link + checksum and audit-log actor/target/bytes/prefix.

**Recovery validation:**
- Export archive integrity check passes checksum verification.
- Legal/compliance tracker marks request as completed within SLA.

**Drill cadence + last drilled date:** monthly synthetic DSAR replay; last drilled 2026-05-04.

---

## RB-009 — Data retention policy misconfiguration

**Owner:** Sec eng.  **SEV target:** SEV2 if active data was deleted early; SEV3 otherwise.

**Symptoms / alert fire:**
- Compliance check reports retention rules drift.
- Unexpected lifecycle deletions or unexpectedly retained records.

**First 5-minute triage:**
1. Identify impacted tenant and dataset from the alert payload.
2. Inspect configured retention policy:
   ```bash
   loop admin retention get --tenant <tenant-id>
   ```
3. Compare object store lifecycle rules:
   ```bash
   aws s3api get-bucket-lifecycle-configuration --bucket <bucket>
   ```

**Mitigation:**
- Pause lifecycle jobs for impacted prefixes.
- Reapply approved baseline from Terraform.
- If early deletion happened, initiate restore from immutable backup and legal/compliance notification.

**Recovery validation:**
- `loop admin retention validate --tenant <tenant-id>` returns success.
- Canary object expiry matches policy in non-production rehearsal.

**Drill cadence + last drilled date:** quarterly policy verification drill; last drilled 2026-05-04.

---

## RB-010 — Region cutover

**Owner:** Eng #2.  **SEV target:** SEV3, scheduled migration.

**Symptoms / alert fire:** planned cross-cloud or regional migration window approved by change-management.

**First 5-minute triage (pre-flight):**
1. Validate target environment readiness (networking, IAM, secrets, observability).
2. Confirm replication lag for Postgres/object stores is within migration thresholds.
3. Confirm rollback plan owner and decision window.

**Mitigation / execution:**
1. Provision target region via Terraform.
2. Replicate Postgres, Qdrant data, and object-store blobs.
3. Run synthetic soak load.
4. Cut workspace `region` routing to target.
5. Keep source in warm-standby during 7-day soak.

**Recovery validation:**
- Error rate/latency/cost stay within SLO in target region during soak.
- No replication drift detected.
- Rollback path tested before source decommissioning.

**Drill cadence + last drilled date:** quarterly migration rehearsal; last drilled 2026-05-04.

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

## RB-012 — Voice POP outage

**Owner:** Eng #3.  **SEV target:** SEV2.

**Symptoms / alert fire:**
- `voice_pop_healthy{pop="<name>"} == 0` for 2 minutes.
- Increased setup failures, packet loss, and one-way audio complaints from a region.

**First 5-minute triage:**
1. Confirm impacted POP and channel provider:
   ```bash
   loop admin voice status --pop <pop>
   ```
2. Verify reachability and SIP health from probe jobs:
   ```bash
   kubectl -n loop-data logs deploy/voice-prober --tail=120
   ```
3. Check failover routing rules in gateway config.

**Mitigation:**
- Route sessions to nearest healthy POP with temporary policy override.
- Reduce max concurrent calls on degraded POP to prevent cascading failures.

**Recovery validation:**
- Probe success rate > 99% for 15 minutes.
- Voice call setup p95 and packet-loss metrics return to SLO.

**Drill cadence + last drilled date:** monthly POP failover drill; last drilled 2026-05-04.

---

## RB-013 — Deploy controller stuck

**Owner:** Eng #2.  **SEV target:** SEV2.

**Symptoms / alert fire:**
- Deploy queues stop draining; rollout state remains `pending` > 10 minutes.
- `loop_deploy_controller_reconcile_errors_total` spikes.

**First 5-minute triage:**
1. Inspect deploy controller status:
   ```bash
   kubectl -n loop-system get pods -l app=cp-deploy-controller
   kubectl -n loop-system logs deploy/cp-deploy-controller --tail=200
   ```
2. Check pending deployments and lock rows:
   ```bash
   loop admin deploy queue ls --state pending
   ```
3. Verify database and message bus connectivity from the controller pod.

**Mitigation:**
- Restart controller pod if stuck worker threads are detected.
- Clear stale lock rows older than threshold with the admin maintenance command.
- Pause new rollout submissions until queue health stabilizes.

**Recovery validation:**
- Pending queue drains to baseline.
- At least one canary and one full rollout complete successfully.

**Drill cadence + last drilled date:** monthly synthetic blocked-queue drill; last drilled 2026-05-04.

---

## RB-014 — Audit log chain integrity check

**Owner:** Sec eng.  **SEV target:** SEV1 if mismatch.

**Symptoms / alert fire:**
- `loop_audit_chain_valid == 0` or scheduled verification job exits non-zero.
- Digest mismatch between Postgres source and ClickHouse mirror.

**First 5-minute triage:**
1. Run verifier:
   ```bash
   loop admin audit verify --workspace=<id_or_all> --since=<date>
   ```
2. Scope impact by workspace and timeframe.
3. Capture immutable copies of relevant audit partitions before remediation.

**Mitigation:**
1. Page CTO + CEO immediately.
2. Suspend writes to primary audit stream; divert to quarantine stream.
3. Capture forensic artifacts: row hashes, Postgres binlog range, ClickHouse mirror segment.
4. Determine likely root cause path (internal privilege misuse vs external compromise).

**Recovery validation:**
- Recomputed chain hash matches expected value over affected range.
- Mirror parity checks pass.
- Post-incident verification passes twice in a row (15 minute interval).

**Drill cadence + last drilled date:** quarterly plus on-demand; last drilled 2026-05-04.

---

## RB-015 — Cross-tenant data-leak suspicion

**Owner:** Sec eng.  **SEV target:** SEV1.

**Symptoms / alert fire:**
- User reports seeing another tenant's data.
- Isolation guardrail alert (`tenant_mismatch_detected_total > 0`) fires.

**First 5-minute triage:**
1. Page CTO + CEO immediately.
2. Identify affected tenant IDs from trace/audit records.
3. Freeze potentially impacted endpoints:
   ```bash
   loop admin route set --name /v1/runtime/stream --mode maintenance
   ```
4. Snapshot logs/traces for forensic retention.

**Mitigation:**
- Disable affected model/tool paths or retrieval component.
- Apply emergency tenant hard-filter at query layer.
- Rotate credentials/tokens if leak vector is auth-related.

**Recovery validation:**
- Synthetic cross-tenant isolation suite passes.
- Manual validation with two sandbox tenants confirms strict data separation.
- Incident communications and regulatory notifications tracked to completion.

**Drill cadence + last drilled date:** quarterly tabletop + monthly synthetic isolation tests; last drilled 2026-05-04.

---

## RB-016 — Vault unsealed required

**Owner:** Eng #2.  **SEV target:** SEV1.

**Symptoms / alert fire:**
- Secret reads fail with Vault sealed errors.
- Control-plane decrypt calls fail across multiple services.

**First 5-minute triage:**
1. Confirm Vault seal state:
   ```bash
   kubectl -n loop-secrets exec deploy/vault -- vault status
   ```
2. Validate whether issue is single pod or full cluster.
3. Confirm unseal key custody and quorum availability.

**Mitigation:**
- Execute approved unseal procedure with quorum key holders.
- Restart dependent services only after Vault reports unsealed and active.
- If unseal cannot complete, fail closed on privileged operations and enable degraded read-only mode.

**Recovery validation:**
- `vault status` returns `Sealed false`.
- Secret read canary passes from control-plane and runtime pods.
- Error rate on decrypt operations returns to baseline.

**Drill cadence + last drilled date:** monthly controlled unseal rehearsal in staging; last drilled 2026-05-04.

---

## RB-017 — Channel provider credential revoked

**Owner:** Eng #7.  **SEV target:** SEV2 per affected channel.

**Symptoms / alert fire:**
- Sudden 401/403 spikes from SMS/email/voice channel provider APIs.
- Delivery success drops below channel SLO.

**First 5-minute triage:**
1. Identify impacted provider and workspace set.
2. Validate credential status:
   ```bash
   loop admin channel creds check --provider <provider>
   ```
3. Check secret age/rotation history and recent changes.

**Mitigation:**
- Rotate provider key or OAuth client secret.
- Switch traffic to backup provider where configured.
- Throttle retries to avoid lockouts/rate-ban escalation.

**Recovery validation:**
- Provider API auth success > 99% for 15 minutes.
- Delivery receipts recover to baseline.

**Drill cadence + last drilled date:** monthly credential-rotation drill; last drilled 2026-05-04.

---

## RB-018 — Mass deploy rollback

**Owner:** Eng #2.  **SEV target:** SEV1.

**Symptoms / alert fire:**
- Elevated runtime error rates or latency immediately following rollout.
- Customer-visible failures correlated with a new deployment version.

**First 5-minute triage:**
1. Identify offending version and rollout percentage.
2. Verify blast radius (tenants/channels/features impacted).
3. Trigger rollback:
   ```bash
   loop admin deploy rollback --agent=<id> --target=<previous-version>
   ```

**Mitigation:**
- Pause additional rollout waves.
- Force previous stable version as pin.
- Disable eval-gating override until fix and additional test coverage are in place.

**Recovery validation:**
- `kubectl rollout status deploy/dp-runtime` succeeds.
- Error/latency metrics return to baseline over two consecutive 5-minute windows.

**Drill cadence + last drilled date:** monthly synthetic rollback drill; last drilled 2026-05-04.

---

## RB-019 — Hire onboarding (Day 1 access)

**Owner:** CTO.  **SEV target:** SEV3.

**Symptoms / alert fire:**
- New hire cannot access required systems on first day.
- Missing least-privilege role grants or SSO provisioning issues.

**First 5-minute triage:**
1. Confirm identity exists in IdP and expected groups are assigned.
2. Verify GitHub, cloud, pager, and ticketing access status.
3. Check onboarding checklist completion for role template.

**Mitigation:**
- Apply standard role bundle for the hire track (eng/security/data).
- Grant temporary break-glass access with explicit expiry if blocker is critical.
- Escalate IdP sync issues to IT operations.

**Recovery validation:**
- Hire can authenticate and complete Day-1 smoke tasks.
- Access review confirms no over-privileged grants.

**Drill cadence + last drilled date:** weekly during active hiring; last drilled 2026-05-04.

---

## RB-020 — Compromised API key

**Owner:** Sec eng.  **SEV target:** SEV1.

**Symptoms / alert fire:**
- Anomalous traffic or spend pattern tied to a single API key.
- Secret-scanning or external report confirms key exposure.

**First 5-minute triage:**
1. Revoke or disable the suspected key immediately.
2. Identify affected tenant/workspace and request path.
3. Pull recent audit events for that key fingerprint.

**Mitigation:**
- Rotate key and notify customer owner with re-issuance instructions.
- Block abusive IP/user-agent signatures at edge.
- Increase auth anomaly monitoring threshold sensitivity for 24h.

**Recovery validation:**
- No further requests accepted with revoked fingerprint.
- Replacement key usage is normal and authorized.
- Post-rotation audit review confirms no lateral compromise.

**Drill cadence + last drilled date:** monthly key compromise simulation; last drilled 2026-05-04.

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

## RB-022 — ClickHouse snapshot restore drill

**Owner:** Eng #4.  **SEV target:** SEV2, **RTO ≤ 90 min**, RPO ≤ 30 min.

**Companion:** `engineering/DR.md` §2.4 (ClickHouse backup strategy), `scripts/dr_clickhouse_restore_drill.sh` (drill driver), `engineering/PERFORMANCE.md` §"Trace ingestion".

**Purpose:** prove that a daily `clickhouse-backup` S3 snapshot can be restored into a fresh cluster and that gap data (anything between the snapshot and now) can be re-ingested from NATS retention + the trace archive. Drill maps to SOC2 control CC7.5 ("backup restoration") and the published trace-store **RPO ≤ 30 min**.

**Scope:** ReplicatedMergeTree tables in the `traces` and `usage` databases. Materialized views are recreated from migration files (`packages/runtime/migrations/clickhouse/`); no MV state needs to be restored.

### Preconditions

- `loop-clickhouse-backup-<region>` bucket reachable from the drill VPC (read-only IAM role on the snapshot prefix).
- `clickhouse-backup` v2.4+ available in the drill image.
- NATS retention bucket addressable for the gap-replay step (`nats stream ls` shows >= 30 min retention).

### Steps (target wall-clock budgets)

| #  | Step                                                                                          | Budget | Cumulative |
| -- | --------------------------------------------------------------------------------------------- | ------ | ---------- |
| 1  | Acknowledge drill kickoff in `#dr-drills`; record `T0` UTC.                                   | 1 min  | 1 min      |
| 2  | Pick the target snapshot (default: most recent successful daily snapshot).                    | 1 min  | 2 min      |
| 3  | Provision the drill cluster (1 shard × 1 replica is enough for verification).                 | 8 min  | 10 min     |
| 4  | `clickhouse-backup download <snapshot>` from S3 into the drill node.                          | 18 min | 28 min     |
| 5  | `clickhouse-backup restore --schema --data <snapshot>`; recreate replicated table metadata.   | 25 min | 53 min     |
| 6  | Replay NATS gap stream (`subjects=traces.*,usage.*`) since `<snapshot.created_at>`.           | 15 min | 68 min     |
| 7  | Smoke checks: row counts on `traces.spans`, `usage.events`; sentinel hash on `traces.spans`.  | 8 min  | 76 min     |
| 8  | Validation queries (sample p95 latency, error-rate aggregations) match prod within ±5%.       | 4 min  | 80 min     |
| 9  | Drill teardown: tear down the drill cluster, archive driver log to `s3://loop-dr-evidence/`.  | 5 min  | 85 min     |
| 10 | File the drill report row in this runbook §Recent drills.                                    | 1 min  | 86 min     |

**Total budget: 86 min — 4 min slack on the 90 min RTO.** Step 5 is the tail risk; if `clickhouse-backup restore` exceeds 1.5× budget, fall back to per-table restore (see Anti-patterns).

### Drill driver invocation

```bash
./scripts/dr_clickhouse_restore_drill.sh \
  --region=us-east-1 \
  --snapshot=2026-05-01-daily \
  --bucket=s3://loop-clickhouse-backup-us-east-1
```

The driver writes a structured log to stdout (one JSON line per step) which the report-archival step uploads verbatim. Same schema as RB-021.

### Recent drills

| Date       | Region        | Driver       | Wall-clock | Result    | Notes                                                       |
| ---------- | ------------- | ------------ | ---------- | --------- | ----------------------------------------------------------- |
| 2026-05-01 | us-east-1     | synthetic CI | 81 min     | ✅ pass    | Restore 24m11s; gap replay covered 23 min from NATS.        |

First real-region drill scheduled for the M3 hardening week; cadence thereafter is **monthly automated** (CI-driven) and **quarterly manual** (engineer-on-call).

### Anti-patterns

- ❌ Restoring the snapshot directly into a production cluster's namespace. Always provision a `clickhouse-drill-*` namespace; the driver refuses if the target name does not match the prefix.
- ❌ Skipping the NATS gap replay. Without it the verified RPO is "snapshot age" (up to 24 h), not 30 min, which silently breaks the trace SLO.
- ❌ Restoring all tables in one shot when a single table is corrupted. `clickhouse-backup restore --tables=db.table` is the lower-blast-radius path for partial corruption.
- ❌ Promoting the drill cluster to live traffic. Drill clusters are torn down at step 9; if the prod cluster is gone, run RB-022 first to validate the snapshot, then provision the real replacement separately.

### Evidence captured

For each drill, the following are uploaded to `s3://loop-dr-evidence/<date>/`:

- `driver.log` — full structured driver output.
- `step-timings.tsv` — one row per step with budget vs actual.
- `smoke.json` — row counts, sentinel hash, validation query diffs.
- `cluster-events.txt` — `kubectl get events` from the drill namespace.

The Vanta evidence collector pulls `step-timings.tsv` weekly and asserts every row's `ok=true` (control CC7.5).

---

## RB-023 — Object-store replication integrity failure

**Owner:** Eng #2.  **SEV target:** SEV2, **RTO ≤ 30 min** (resume replication or accept gap).

**Companion:** `engineering/DR.md` §2.3 (object-storage strategy), `scripts/objstore_integrity_check.sh` (daily integrity driver).

**Symptoms:** PagerDuty alert "objstore replication integrity failures > 0 for 2 runs" (Prometheus metric `loop_objstore_replication_integrity_failures > 0` at 04:17 + 04:17 next day) **or** the `objstore-integrity-check` CronJob's TSV manifest contains rows with `status=missing` / `status=etag-mismatch`.

### Steps

1. **Acknowledge** in `#inc-YYYYMMDD-objstore`. Record `T0`.
2. **Pull the latest manifest:**
   ```bash
   aws s3 cp s3://loop-dr-evidence/objstore-integrity/$(date -u +%F)/integrity.tsv .
   awk -F'\t' '$5 != "ok"' integrity.tsv | head -50
   ```
3. **Categorise** the failures:
   - `status=missing` — source object not yet replicated to destination.
   - `status=etag-mismatch` — replicated but content differs (rare; usually means a re-upload raced replication).
   - `status=size-mismatch` — truncated transfer; treat as `etag-mismatch`.
4. **For `missing` only**, check the cloud provider replication queue:
   - AWS: `aws s3api get-bucket-replication --bucket <src>` and the `ReplicationLag` CloudWatch metric.
   - Self-host MinIO: `mc admin replicate status <alias>`.
   If lag is rising, page the replication primary owner and **escalate to SEV1**.
5. **For mismatch** rows, run the targeted re-replicate helper:
   ```bash
   ./scripts/objstore_integrity_check.sh repair --manifest integrity.tsv
   ```
   The repair pass re-uploads only the offending keys with `--metadata-directive REPLACE`, which forces a fresh replication event.
6. **Re-run** the integrity check at the end of the response window:
   ```bash
   ./scripts/objstore_integrity_check.sh --bucket=<src> --dest=<dst>
   ```
   Expect `failures=0`. If not, the bucket is in a degraded state — freeze writes via `loop admin objstore freeze --bucket=<src>` and escalate.
7. **Status page** update only if customer-visible (audit-log retrieval slowness, KB document fetch errors).
8. **PIR** if the failure persisted >24h or impacted any customer.

### Recent drills

| Date       | Region        | Driver       | Wall-clock | Result    | Notes                                                |
| ---------- | ------------- | ------------ | ---------- | --------- | ---------------------------------------------------- |
| 2026-05-02 | us-east-1     | synthetic CI | 12 min     | ✅ pass    | Injected 3 mismatched objects; repair caught all 3.  |

### Anti-patterns

- ❌ Treating a single `missing` row as urgent. Replication is eventually consistent; the integrity check tolerates a per-object grace window of 15 min before flagging. If a row appears in *two* consecutive daily manifests, *then* it is a real failure.
- ❌ Force-deleting the destination bucket to "reset" replication. You lose history and break MFA-delete invariants. Re-replicate per-key.
- ❌ Skipping step 6 (post-repair verification). Without it the manifest stays red and the alert keeps firing.

### Evidence captured

The CronJob writes daily to `s3://loop-dr-evidence/objstore-integrity/<date>/`:

- `integrity.tsv` — one row per object (`bucket\tkey\tsource_etag\tdest_etag\tstatus`).
- `summary.json` — `{checked, ok, missing, mismatch, started_at, ended_at}`.
- `prom.txt` — the Prometheus exposition snippet that `kube-prometheus` scrapes.

The Vanta evidence collector pulls `summary.json` daily and asserts `failures == 0` (control CC7.5 / A1.2 "backups are restorable AND replicated").

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

---

## RB-024 — BYO Vault credential rotation

**Owner:** Sec eng. **SEV target:** SEV2 if rotation is overdue; SEV1 if a credential leak is suspected.

**Scope:** Tenants that bring their own HashiCorp Vault cluster (configured via `VaultConfig` in `packages/control-plane/loop_control_plane/byo_vault.py`). Loop authenticates to the customer's Vault using AppRole; Loop holds the `role_id` per workspace and fetches a wrapped `secret_id` from a customer-side endpoint per request lease. Rotation here means: (a) rotating the AppRole `role_id` because the customer rolled it, or (b) rotating the wrapping endpoint URL/credential.

**Symptoms / alert fire:**
- `LOOP-API-403 byo_vault_auth_failed` in cp-api logs after a customer-side Vault change.
- Customer notifies us out-of-band that they rolled the AppRole.
- Periodic rotation cadence (90 days; tracked in the rotation calendar).

**First 5-minute triage:**

1. **Acknowledge** the page or scheduled rotation ticket. Open `#byo-vault-rotate-<workspace>`.
2. **Pause writes** that depend on BYO Vault for the affected workspace:
   ```bash
   loopctl workspace pause-byo-vault --workspace <id> --reason "rotation"
   ```
3. **Confirm new role_id with the tenant** through the agreed secure channel (signed email or shared 1Password). Do **not** accept role_ids over Slack or unencrypted channels.

**Mitigation:**

4. **Update the workspace BYO Vault config** via the cp-api admin endpoint:
   ```bash
   loopctl workspace set-byo-vault \
     --workspace <id> \
     --address <https://vault…> \
     --role <new-role-id> \
     [--namespace <ns>] \
     [--mount-path <path>]
   ```
   The new value lands in the `byo_vault_configs` table; existing in-flight reads continue using the old value until the next fetch.
5. **Verify** by issuing a probe secret read against a known test path:
   ```bash
   loopctl workspace probe-byo-vault --workspace <id> --path test/canary
   ```
   Expect a 200 with the canary value. A 403 means the new role isn't yet trusted by the customer's Vault — coordinate with the tenant.
6. **Resume writes**:
   ```bash
   loopctl workspace resume-byo-vault --workspace <id>
   ```
7. **Audit-log entry** is written automatically by the cp-api handler (`workspace.byo_vault.rotate`); confirm it appears in the workspace audit log.
8. **Update the rotation calendar** with the new rotation due date (today + 90 days).
9. **If a leak is suspected** (SEV1 escalation): immediately call `loopctl workspace pause-byo-vault`, notify the tenant security contact via the IR runbook channel, and treat per `engineering/SECURITY.md` incident response.

**Recovery validation:**
- `loopctl workspace probe-byo-vault --workspace <id> --path test/canary` returns 200 with expected canary.
- No new `byo_vault_auth_failed` errors for 15 minutes.
- Audit event `workspace.byo_vault.rotate` is present with the correct actor and workspace id.

**Drill cadence + last drilled date:** quarterly synthetic credential-rotation rehearsal; last drilled 2026-05-04.

### Recent drills

| Date       | Scope                    | Result | Notes |
| ---------- | ------------------------ | ------ | ----- |
| 2026-05-04 | synthetic design-partner | ✅ pass | role_id update + probe read + audit verification |

### Anti-patterns

- **Do not** store the `role_id` in source control or in our own Vault — it is per-tenant data and lives only in the `byo_vault_configs` Postgres row protected by RLS.
- **Do not** keep the old `role_id` "for rollback"; once the tenant rolls the AppRole, the old value is invalid, and keeping it adds blast radius.
- **Do not** rotate without pausing writes — partial reads with the old role surface confusing 403s in logs and delay actual rotation discovery.
