# support_agent

A reference Loop agent that handles customer support requests for an online
retailer. Demonstrates:

- a function tool (`lookup_order`) that returns structured data
- an MCP-mounted KB tool for searching the support knowledge base
- per-tier memory: persistent user, session-scoped TTL, and per-run scratch
- hard caps (`max_iterations`, `max_cost_usd`) for predictable spend
- an eval suite with LLM-judge, latency, and cost scorers

## Run locally

Prereqs: `uv` 0.5+, the Loop docker-compose stack up
(`make up` from the repo root).

```sh
# load required env vars (anthropic key, kb id, etc.)
cp .env.example .env

# start the agent in dev mode (hot-reload)
uv run loop dev examples/support_agent

# in another shell, send it a message
uv run loop chat examples/support_agent "Where is order 4172?"
```

## Run the eval suite

```sh
uv run python examples/support_agent/run_eval.py
```

The suite asserts a 0.7 LLM-judge pass rate, no hallucinations, latency under
2 s, and cost under $0.01 per turn. Results print as a Markdown table.

## Files

| File | Purpose |
| --- | --- |
| `agent.py` | Agent definition (instructions, tools, memory, caps) |
| `evals/suite.yaml` | Declarative eval cases + scorers |
| `run_eval.py` | Loads the suite into `loop_eval.EvalRunner` |
| `.env.example` | Required configuration values |

## Customising

- Swap `claude-sonnet-4-7` for any model your gateway exposes by editing
  `agent.py`.
- Add tools by decorating async functions with `@tool` and listing them on
  the `tools` attribute.
- Tighten caps via `max_iterations` / `max_cost_usd` to match your SLOs.
