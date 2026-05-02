# Perf Regression Budget

S846 adds a PR-blocking regression gate for the committed performance
contracts under `bench/results/`.

The gate runs `scripts/perf_regression_budget.py` against
`bench/results/perf_7d_baseline.json`, which stores the last 7-day p95 baseline
for each hard acceptance gate. Any 5%+ p95 regression fails the PR workflow and
pages on-call through `LOOP_ONCALL_WEBHOOK_URL`.

The current budget covers:

- control-plane API 5000 RPS
- KB retrieval at 1M synthetic chunks
- runtime 100 turns/minute
- runtime SSE at 1000 concurrent turns
- tool-host warm start
- text-turn k6 latency
- voice p50 gate p95 guardrail

The workflow writes `bench/results/perf_regression_budget.json` as the compact
CI contract and uploads it as the `perf-regression-budget` artifact.
