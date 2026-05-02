# Tool-host warm-start gate

Loop keeps tool sandboxes prewarmed so MCP tool calls avoid cold-start latency.
The S843 gate measures the warm-acquire path and fails when p95 reaches 300 ms.

## Run locally

```sh
uv run python scripts/tool_host_warm_start.py \
  --output bench/results/tool_host_warm_start.json \
  --target-p95-ms 300
```

The benchmark prewarms the `WarmPool`, measures repeated acquire/release
cycles, writes `bench/results/tool_host_warm_start.json`, and exits non-zero
when p95 breaches the target. CI uploads the report and pages on-call on
failure.
