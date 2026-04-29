# Loop — Disaster Recovery

**Status:** v0.1  •  **Owner:** Eng #2 (Infra) + Sec eng
**Companions:** `engineering/RUNBOOKS.md` (per-failure runbooks), `engineering/SECURITY.md` §10 (incident response).

DR is the discipline of "we lost X — what now?" Loop's commitments are explicit, testable, and small in scope so we can credibly hit them.

---

## 1. Recovery objectives

| Class | What's at stake | RTO | RPO |
|-------|-----------------|-----|-----|
| Single pod loss | One runtime / channel pod | < 30 s | 0 (NATS replays in-flight events) |
| Single AZ loss | One AZ in a region | ≤ 2 min | 0 (multi-AZ replication) |
| Region primary DB failover | Postgres primary down, secondary takes over | ≤ 5 min | ≤ 30 s |
| Region object-store outage | S3-equivalent down | ≤ 30 min | varies — recordings/artifacts may be unavailable until recovery |
| Region full loss | Entire data plane region offline | ≤ 4 h | ≤ 5 min via cross-region async replication of critical data |
| Region permanent loss | Region destroyed (catastrophic) | ≤ 24 h | ≤ 1 h |
| Control-plane region loss | API + Studio + billing offline globally | ≤ 1 h | ≤ 5 min |
| Full provider compromise | Cloud account suspended / breached | ≤ 72 h | ≤ 24 h (last full backup) |
| Customer key destruction (BYOK) | Customer destroys their KMS key | irrecoverable by design — that's the feature | n/a |

**Notes:**
- "RTO ≤ X" means we commit to restoring service within X of detection.
- "RPO ≤ Y" means the most data we may permanently lose is Y of the most recent activity.
- These are SLOs we publish on the status page. Enterprise plans tighten RTO 2× via dedicated infra.

---

## 2. Backups

### 2.1 Postgres

- **Continuous WAL archiving** to S3-compatible object storage (per-region) every 5 min.
- **Daily logical dumps** retained 14 days.
- **Weekly logical dumps** retained 90 days.
- **PITR window:** 14 days (standard), 90 days (Enterprise).
- **Encryption:** WAL-G envelope encrypts every backup with the workspace's KMS data key. Destroying the KMS key invalidates the backup — feature, not bug.
- **Test:** monthly automated restore-and-verify of a random sample workspace into a sandbox region; row-counts compared to source.

### 2.2 Qdrant

- **Snapshots** every 6 hours, retained 30 days.
- **Replication factor:** 2 in cloud. (Self-host is configurable; we recommend 2 minimum.)
- **Test:** monthly automated snapshot restore.

### 2.3 Object storage

- **Versioning** enabled on every Loop bucket (cloud-native object versioning).
- **MFA-delete** required for retention-protected paths (recordings, audit-log archives).
- **Cross-region replication** for `audit-log/` and `kb-originals/` only. Recordings + traces stay in-region for cost reasons; loss bounded by RPO.

### 2.4 ClickHouse

- ReplicatedMergeTree across 2 replicas in-region.
- 24h S3 backup snapshots (`clickhouse-backup`), retained 30 days.
- Sustained loss → re-ingest from NATS retention (30 min) + S3 archive (90 days). Latest data within 30 min may be lost in catastrophic failures (matches the trace RPO above).

### 2.5 Vault

- Vault Raft snapshots every 1 h, encrypted with a separate cold-storage KMS key, replicated cross-region.
- Loss-of-quorum triggers `RB-016` (Vault unsealed required).

---

## 3. Region full-loss playbook

Trigger: provider declares region unavailable for > 30 min OR catastrophic event.

### 3.1 Read-only fallback (T+0 to T+30 min)

1. Front-door (Cloudflare) flips the affected region's hostname to a maintenance page that returns 503 + `Retry-After: 1800`.
2. Studio shows global banner: "Region X is down; new conversations are paused. Existing in-flight conversations will not lose data."
3. Channel webhook ingestion is suspended for the affected region; channel providers will retry.

### 3.2 Restore in target region (T+30 min to T+4 h)

1. Provision a target region via Terraform (`infra/terraform/envs/dr-<region>/`). Pre-staged in a different cloud if `CROSS_CLOUD_DR=true`.
2. Restore Postgres from the latest cross-region backup. Verify row counts.
3. Restore Qdrant from the latest snapshot (per-workspace collections).
4. Restore object storage from cross-region replication (audit log + KB originals).
5. ClickHouse: empty start; replay last 30 min from NATS, then re-ingest from archive for the rest.
6. Update region resolution in `regions.yaml`; the affected workspaces now point at the new infra.
7. Bring up `dp-runtime` pods; warm pool fills.
8. Take down the maintenance page.

### 3.3 Communicate

- Status page updated every 30 min during outage.
- Customer-success team contacts every Enterprise customer in the affected region within 1 h.
- Public PIR within 7 days.

### 3.4 Reconcile

- Compare audit logs between primary and replica; flag any chain breaks.
- Identify any conversations that lost data (RPO breach) and contact those workspaces specifically.
- Refund credits at our discretion per the SLA.

---

## 4. Drill cadence

| Drill | Frequency | Owner | Pass criteria |
|-------|-----------|-------|----------------|
| Pod kill (random) | Weekly (chaos day) | Eng #2 | RTO ≤ 30 s, no errors visible |
| Postgres failover | Monthly | Eng #2 | RTO ≤ 5 min, RPO ≤ 30 s |
| Region failover | Quarterly | Eng #2 + Sec eng | RTO ≤ 4 h, RPO ≤ 5 min |
| Cross-cloud DR | Twice yearly | Eng #2 | Restore an AWS region's data into a GCP region; pass criteria same as region failover |
| Vault unseal | Quarterly | Eng #2 | Ops can unseal within 10 min using key shards |
| Backup restore validation | Monthly automated | Eng #2 | Row-count match, hash-spot-check pass |
| Customer-side runbook walk-through | Quarterly | Sec eng | Every Enterprise customer on the runbook for their plan |

Drills are mandatory; missed drills are a SEV3 incident in their own right.

---

## 5. Cross-cloud DR (advanced)

For Enterprise customers who require cloud-vendor diversity:

- Primary data plane on cloud A.
- Cross-region replication of critical data into cloud B (different region of B, even).
- Quarterly drill that boots the B-side and serves a synthetic workspace.

This is opt-in and adds ~30% to infra cost. Available for Enterprise plans only.

---

## 6. What is NOT covered by DR

These failure modes are out of scope (loss is permanent, by design):

- **Customer destroys their BYOK key.** Backups encrypted with that key become unrecoverable cipher.
- **Customer issues a DSAR-erasure for an end user.** That user's data is cryptographically erased from all backups within the next backup cycle (≤ 14 days for standard plans).
- **Sub-RPO data.** The most recent N seconds (per the RPO table above) before a regional event may be lost.
- **In-flight LLM responses.** If a turn was mid-LLM-call when the region died, the gateway reissues with a fresh `request_id`; the customer sees a transient error, not a permanent one. No "exactly-once" semantic is offered for paid tokens.
- **Self-hosted customer DR.** We document the procedures; we do not operate the customer's environment.

---

## 7. Compliance mapping

| Standard | Control | Loop evidence |
|----------|---------|---------------|
| SOC2 CC7.1 | DR plan exists, tested annually | this doc + drill records |
| SOC2 CC7.2 | Backup procedures documented | §2 |
| SOC2 CC7.3 | Backup integrity verified | §2.1 monthly restore-and-verify |
| GDPR Art. 32 | Resilience of processing systems | §1 RTO/RPO + §4 drills |
| HIPAA §164.308(a)(7)(ii)(B) | Disaster recovery plan | this doc |
| ISO 27001 A.17.1 | Information security continuity | §3 |

---

## 8. References

- `engineering/SECURITY.md` §11 — data lifecycle + retention policy.
- `engineering/RUNBOOKS.md` — RB-001, RB-002, RB-003, RB-004, RB-016.
- `architecture/CLOUD_PORTABILITY.md` §13 — cross-cloud rclone migration playbook.
