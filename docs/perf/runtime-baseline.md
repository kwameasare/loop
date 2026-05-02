# Runtime baseline: 100 turns/minute

This is the S142 baseline for the `dp-runtime` text-turn path: 100 turns per
minute for 5 minutes against `/v1/turns`.

| Metric | Value |
|--------|-------|
| p50 latency | 1 ms |
| p95 latency | 2 ms |
| p99 latency | 3 ms |
| error rate | 0.0% |
| request rate | 100 turns/min |

Run the baseline locally:

```sh
k6 run --summary-export /tmp/runtime-baseline-100rpm.json \
  scripts/k6_runtime_baseline_100rpm.js
```

The committed contract is `bench/results/runtime_baseline_100rpm.json`.
