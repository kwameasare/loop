# Loop docs

Welcome. Loop is the agent-first control plane: design, deploy, observe, and
evaluate AI agents that talk to real users on real channels.

## Start here

- [Quickstart](./quickstart.md) — five minutes from clone to first turn.
- [Cookbook: Support agent](./cookbook/support_agent.md) — a worked example
  you can copy.

## Concepts

- [Agents](./concepts/agents.md) — instructions, tools, memory, caps.
- [Tools](./concepts/tools.md) — function tools, MCP, dispatch model.
- [Memory](./concepts/memory.md) — user, session, scratch tiers.
- [Channels](./concepts/channels.md) — web widget, Slack, WhatsApp, voice.
- [Eval](./concepts/eval.md) — scorers, replay, eval-gated deploys.

## Operations

- [Branch protection](./branch-protection.md) — required CI checks for `main`.
- [Cloud portability proof](./CLOUD_PROOF.md) — capability matrix and nightly
  GREEN/RED smoke marks.
- [cp-api 5000 RPS](./perf/cp_api_5000_rps.md) — sustained control-plane
  API acceptance gate.
- [Gateway cache hit-ratio](./perf/gateway_cache_hit_ratio.md) — nightly
  semantic-cache effectiveness gate.
- [Gateway provider eval](./perf/gateway_provider_eval.md) — nightly
  provider quality, latency, and cost matrix.
- [KB retrieval 1M](./perf/kb_retrieval_1m.md) — nightly synthetic
  million-chunk retrieval p50 gate.
- [Perf regression budget](./perf/perf_regression_budget.md) — PR-blocking
  p95 comparison against the 7-day baseline.
- [Runtime SSE 1000-concurrency](./perf/runtime_sse_1000_concurrency.md)
  — high-concurrency streaming acceptance gate.
- [Runtime baseline](./perf/runtime-baseline.md) — 100 turns/minute
  latency report.
- [Tool-host warm-start](./perf/tool_host_warm_start.md) — nightly WarmPool
  p95 budget gate.
- [Voice performance](./perf/voice_perf.md) — nightly p50 latency acceptance
  gate.

## Security & policy

- [Threat model](./THREAT_MODEL.md) — adversary model, trust boundaries,
  and per-component mitigations.
- [Bug bounty program](./site/bug-bounty.md) — scope, severity rewards,
  and submission workflow.
- [Security acknowledgements](./site/acknowledgements.md) — researchers
  credited for accepted reports.
- [Data retention policy](./site/data-retention.md) — retention windows
  per data class and deletion guarantees.
- [Pricing verification](./site/pricing-verification.md) — how published
  prices map to actual billed line items.
- [Partner reviews](./site/PARTNER_REVIEWS.md) — design-partner case
  studies and quoted feedback.

## How docs are organised

```
docs/
  index.md              # this file
  quickstart.md         # zero-to-first-turn walkthrough
  CLOUD_PROOF.md        # cloud portability proof matrix
  concepts/             # the conceptual model
    agents.md
    tools.md
    memory.md
    channels.md
    eval.md
  perf/
    cp_api_5000_rps.md
    gateway_cache_hit_ratio.md
    gateway_provider_eval.md
    kb_retrieval_1m.md
    perf_regression_budget.md
    runtime-baseline.md
    runtime_sse_1000_concurrency.md
    tool_host_warm_start.md
    voice_perf.md
  cookbook/             # opinionated, end-to-end examples
    support_agent.md
```

If a page is missing from this map but exists on disk, the navigation
manifest test (`tools/check_docs_links.py`) will fail.
