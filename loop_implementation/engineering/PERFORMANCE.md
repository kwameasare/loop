# Loop — Performance Budgets & Bench Rig

**Status:** v0.1  •  **Owner:** Founding Eng #1 (Runtime) + Eng #2 (Infra) + Eng #3 (Voice)
**Companions:** `engineering/TESTING.md` §6 (load), `architecture/ARCHITECTURE.md` §9 (NFRs)

This is the canonical reference for what "fast enough" means at Loop, the rig we measure against, and the gates that block merges that regress performance.

---

## 1. Budgets

These are **hard contracts**. A PR that regresses any of them by > 10% (vs the rolling 7-day baseline) is blocked from merge unless the regression is justified in the PR body and approved by the relevant owner.

### 1.1 User-visible

| Surface | Metric | p50 | p95 | p99 | Owner |
|---------|--------|-----|-----|-----|-------|
| Voice end-to-end | first-audio after user end-of-speech | 700 ms | 1100 ms | 1500 ms | Eng #3 |
| Chat — first token | inbound msg → first token to channel | 600 ms | 1200 ms | 2000 ms | Eng #1 |
| Chat — full turn | inbound msg → last token | 2.0 s | 4.0 s | 8.0 s | Eng #1 |
| Studio — page LCP | Largest Contentful Paint on conversation list | 1.0 s | 1.5 s | 2.5 s | Eng #5 |
| Studio — trace open | click conversation → trace fully rendered | 400 ms | 800 ms | 1500 ms | Eng #5 |
| API — non-LLM endpoints | server-side response time | 80 ms | 200 ms | 500 ms | Eng #2 |
| Trace ingest lag | event time → visible in Studio | 2 s | 4 s | 5 s | Eng #4 |
| Deploy time | `loop deploy` → live in cluster | 30 s | 45 s | 60 s | Eng #2 |
| Eval suite (100 cases) | full run | 60 s | 80 s | 90 s | Eng #4 |

### 1.2 Internal hot paths

| Operation | Target | Notes |
|-----------|--------|-------|
| Memory load (cold) | ≤ 50 ms p99 | Postgres + Redis fan-out |
| Memory load (warm cache) | ≤ 5 ms p99 | Redis-only |
| Prompt builder | ≤ 5 ms p99 | Pure CPU |
| Tool dispatch (in-process) | ≤ 1 ms p99 | Just a function call |
| Tool dispatch (sandboxed, warm) | ≤ 100 ms p99 | Firecracker pool |
| Tool dispatch (sandboxed, cold) | ≤ 250 ms p99 | First request to a new tool |
| OTel span export | < 1% turn latency | Async, batched |
| RLS-scoped Postgres SELECT | ≤ 10 ms p99 (workspace-scoped) | Index-driven |
| Qdrant top-k=10 (5M points) | ≤ 25 ms p99 | Hybrid search |
| LLM gateway dispatch overhead | ≤ 10 ms p99 | Plus provider time |

### 1.3 Capacity (per data-plane region)

| Concern | MVP target | M9 target | M12 target |
|---------|-----------|-----------|-----------|
| Concurrent conversations / pod | 100 | 250 | 500 |
| Conversations per region | 10K | 50K | 250K |
| Turns per second per region | 50 | 250 | 1000 |
| Voice calls concurrent per region | 20 | 100 | 500 |
| KB chunks indexed per region | 1M | 50M | 500M |
| MCP tools concurrent | 50 | 250 | 1000 |

---

## 2. Bench rig

### 2.1 Tooling

| Layer | Tool | Output |
|-------|------|--------|
| Python microbench | `pytest-benchmark` (with `--benchmark-json=…`) | JSON, committed to `bench/results/` |
| HTTP load | `k6` (CSV + InfluxDB output) | InfluxDB → Grafana dashboard |
| User-journey load | `locust` | HTML report; CI artifact |
| Voice leg | custom `siplaunch` driver + `bla` (built-in) | JSON |
| Bench environment | dedicated k8s namespace `bench` on a fixed node-pool (4× c7i.4xlarge or equivalent) | n/a |

### 2.2 Bench cadence

- **Per PR (microbenches only).** `pytest-benchmark --benchmark-only` runs on every push touching `packages/runtime/`, `packages/gateway/`, `packages/kb-engine/`. Results compared to `main`'s last green run; >10% regression blocks.
- **Nightly (full).** Full k6 + locust against staging. Results posted to `#perf` Slack with diffs vs 7-day baseline.
- **Nightly turn-latency gate.** <!-- S840 --> `.github/workflows/turn-latency-k6.yml` deploys the Helm smoke runtime in kind and runs `scripts/k6_turn_latency.js` against `/v1/turns`. The k6 threshold `http_req_duration p(95)<2000` fails CI on breach and the failure path pages `LOOP_ONCALL_WEBHOOK_URL`.
- **Pre-release.** Voice leg + load matrix on every release-candidate.
- **Quarterly.** Cross-cloud comparison run (AWS, GCP, Azure, Alibaba) — same workload, three runs each, results published in the engineering blog.

### 2.3 Golden file format

`bench/results/<benchmark>.json` per microbench:

```json
{
  "name": "TurnExecutor.execute_simple",
  "commit": "abc1234",
  "ts": "2026-04-29T12:00:00Z",
  "host": "ci-runner-pool-3",
  "stats": {
    "mean_ms": 142.3,
    "stddev_ms": 8.1,
    "p50_ms": 140.0,
    "p95_ms": 158.0,
    "p99_ms": 167.5,
    "n": 1000
  },
  "regression_threshold": 0.10,
  "baseline_ref": "main@def5678"
}
```

The CI compares the new run to the file at `main@<baseline_ref>`. Regression = `(mean_new - mean_baseline) / mean_baseline > regression_threshold`.

HTTP-load gates may also commit a compact k6 contract file under `bench/results/`.
For S840, `bench/results/turn_latency_text_path_k6.json` records the text-turn
p95 budget, the source workflow, and the alerting threshold; the nightly k6 run
exports the full raw summary as a CI artifact for time-series comparison.

### 2.4 Flake handling

A bench is "flaky" if its stddev / mean (CV) > 15% across 5 consecutive runs. Flaky benches are not gating but emit a warning. Owner is pinged.

---

## 3. Profiling workflows

### 3.1 Python (runtime, gateway, KB)

- **CPU.** `py-spy record -o profile.svg -- uv run python -m loop.runtime`. View FlameGraph in any SVG viewer.
- **Memory.** `memray run -m loop.runtime` then `memray flamegraph`.
- **Async waiting.** `aiomonitor` exposes the asyncio loop on port 50101 in dev. `aioconsole` to inspect tasks live.
- **Slow query.** Postgres `pg_stat_statements` enabled in prod; queries > 100 ms ship to Sentry with the SQL + plan.

### 3.2 Studio (Next.js)

- **Lighthouse CI** runs on every PR touching `apps/studio/`. Budgets enforced for LCP, TBT, CLS.
- **React Profiler** snapshots committed for the trace and conversation views.
- **Bundle analysis** via `@next/bundle-analyzer`; budget = 250 KB initial JS, 1 MB total.

### 3.3 Voice

- **Real-time captures.** Voice channel records first 30s of every call (with consent flag) for replay debugging.
- **Latency markers.** Every stage (VAD, STT, LLM, TTS) emits a span with `loop.voice.stage` attribute. Grafana dashboard shows breakdown per call.

---

## 4. Common regressions and counter-measures

| Regression | Symptom | Fix |
|------------|---------|-----|
| Cold start hit | first turn 3× p50 | Warm pool size too low; raise `LOOP_RUNTIME_WARM_POOL_SIZE` or pre-provision |
| LLM provider tail latency | sporadic p99 spikes | Pin to lower-tail-latency model; widen retry budget; enable secondary provider |
| Postgres query plan flip | sudden p99 jump | Refresh stats; check for missing index; isolate via `EXPLAIN (ANALYZE, BUFFERS)` |
| Qdrant index rebuild | retrieval p99 doubles | Background rebuild during low traffic; or move to in-place quantization |
| Trace export back-pressure | trace ingest lag > 10 s | Scale OTel collector; increase NATS retention; lower sampling for non-error spans |
| Tool sandbox swap thrash | tool dispatch p99 spike | Increase Firecracker pool size; ensure pre-warmed mages match tool VMs |
| LLM cache miss flood | gateway latency up | Verify cache key stability; raise `LOOP_GATEWAY_CACHE_SIM_THRESHOLD` |

---

## 5. Performance review cadence

- **Weekly:** Eng #1 + Eng #4 review the perf dashboard; regressions identified and ticketed.
- **Monthly:** post a "perf state of the union" in `#perf` (top 5 wins, top 5 regressions).
- **Quarterly:** cross-cloud comparison + bench rig refresh (refresh node-pool, refresh datasets).

---

## 6. References

- `engineering/TESTING.md` §6 — load testing scenarios.
- `architecture/ARCHITECTURE.md` §9 — non-functional requirements.
- `engineering/HANDBOOK.md` §6 — perf budget gating in CI.
