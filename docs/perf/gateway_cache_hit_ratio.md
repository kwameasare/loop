# Gateway cache hit-ratio gate

Loop runs a fixed semantic-cache workload every night to catch cache-key or
embedding regressions before they add provider latency and cost.

The gate passes when `gateway_cache_hit_ratio_fixed_eval` reports a hit ratio
of at least 30%. The workflow uploads `bench/results/gateway_cache_hit_ratio.json`
on every run and pages on-call when the ratio falls below target.

## Fixed workload

The workload is deterministic and provider-free:

- repeated refund, usage-limit, API-key, and Slack-channel prompts;
- the same in-process `SemanticCache` algorithm used by gateway tests;
- cache lookup before store, so first-seen prompts miss and repeated prompts
  must hit.

## Run locally

```sh
uv run python scripts/gateway_cache_hit_ratio.py \
  --output bench/results/gateway_cache_hit_ratio.json \
  --min-hit-ratio 0.30
```

The script exits non-zero when the measured ratio is below the threshold.
