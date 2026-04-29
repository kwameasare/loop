---
name: add-metric
description: Use when adding a Prometheus counter, gauge, histogram, or summary.
when_to_use: |
  - New customer-visible feature → user-visible metric.
  - New external dependency → health metric.
  - New rate-limit / budget → counter + gauge.
required_reading:
  - architecture/ARCHITECTURE.md   # §7.5
  - engineering/HANDBOOK.md         # §5
applies_to: observability
owner: Founding Eng #4
last_reviewed: 2026-04-29
---

# Add metric

## Trigger

User-visible feature or external dep without a metric is invisible to ops. Add one.

## Required reading

`architecture/ARCHITECTURE.md` §7.5.

## Steps

1. **Naming:** `loop_<service>_<verb>_<unit>` snake_case. Examples: `loop_runtime_turns_total`, `loop_gateway_provider_dispatch_latency_seconds`, `loop_kb_qdrant_top_k_latency_seconds`.
2. **Type:**
   - Counter: monotonically increasing (request count, error count).
   - Gauge: instantaneous (queue depth, in-flight conversations).
   - Histogram: latency, sizes (use SLO-aligned buckets).
   - Summary: rare; prefer histogram.
3. **Labels** (low cardinality only): `region`, `cloud`, `provider`, `model`, `channel_type`, `outcome` (`ok|error|degrade`). Never `workspace_id` or `user_id` (cardinality bomb).
4. **Register** centrally in `packages/observability/loop/observability/metrics.py`. Don't define locally.
5. **Dashboard:** add a panel in `infra/grafana/<service>.json`.
6. **Alerts:** if user-visible, add a Prometheus alert rule in `infra/prometheus/alerts/<service>.yaml`. Alert on user-visible symptoms (error rate, latency p99), not internal causes (CPU).
7. **SLO budgets:** if the metric is one we publish (status page), document in `engineering/PERFORMANCE.md` §1.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Naming follows `loop_<service>_<verb>_<unit>`.
- [ ] Right metric type.
- [ ] Low-cardinality labels only.
- [ ] Registered in central registry.
- [ ] Grafana panel added.
- [ ] Alert rule added (if user-visible).

## Anti-patterns

- ❌ `workspace_id` as a label.
- ❌ Histograms with default buckets (set bucket boundaries to your SLO).
- ❌ Metric without a dashboard.
- ❌ Metric without an alert when it's user-visible.

## Related skills

- `observability/add-otel-span.md`, `observability/add-runbook.md`.

## References

- `architecture/ARCHITECTURE.md` §7.5.
