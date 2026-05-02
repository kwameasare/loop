# Chaos Engineering Findings

This file is auto-updated by `chaos/harness.py`.

Drill cadence: **weekly** (every Monday 02:00 UTC) in staging via CI scheduled job.

## SLA reference

| Scenario | SLA limit |
|----------|-----------|
| network_partition | RTO ≤ 60 s |
| db_failover | RTO ≤ 300 s (5 min) — per RB-001 |
| nats_outage | RTO ≤ 60 s — per RB-004 |

---

<!-- harness.py appends drill runs below this line -->
