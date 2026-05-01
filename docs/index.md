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
- [Gateway provider eval](./perf/gateway_provider_eval.md) — nightly
  provider quality, latency, and cost matrix.

## How docs are organised

```
docs/
  index.md              # this file
  quickstart.md         # zero-to-first-turn walkthrough
  concepts/             # the conceptual model
    agents.md
    tools.md
    memory.md
    channels.md
    eval.md
  perf/
    gateway_provider_eval.md
  cookbook/             # opinionated, end-to-end examples
    support_agent.md
```

If a page is missing from this map but exists on disk, the navigation
manifest test (`tools/check_docs_links.py`) will fail.
