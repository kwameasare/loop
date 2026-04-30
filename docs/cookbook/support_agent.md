# Cookbook: Support agent end-to-end

This cookbook walks through `examples/support_agent` end-to-end. By the
end you'll know:

- how the agent class wires up tools and memory
- how the eval suite is structured
- how to swap the deterministic stub for a live gateway call
- how to deploy it through the control plane

## 1. The agent

`examples/support_agent/agent.py` is ~50 lines. The interesting bits:

- `model = "claude-sonnet-4-7"` — picks a gateway model alias.
- `tools = [Tool.fn(lookup_order), Tool.mcp("loop-hub://kb@latest", ...)]`
  — one in-process function tool plus a managed KB.
- `memory = Memory(user="postgres", session=Memory.ttl("24h"), scratch=Memory.in_run())`
  — three-tier memory.
- `max_iterations = 6`, `max_cost_usd = 0.10` — hard caps.

## 2. The eval suite

`examples/support_agent/evals/suite.yaml` declares:

- three cases: `where_is_my_order`, `refund_basic`, `out_of_scope`
- four scorers: LLM judge, hallucination, latency ≤ 2 s, cost ≤ $0.01
- expected tool calls per case (machine-checkable)

`examples/support_agent/run_eval.py` loads the YAML, hands the cases to
`EvalRunner`, and prints a Markdown table. CI runs this script with a
deterministic stub agent so it doesn't need an Anthropic key. Locally
you can swap `_stub_agent` for an adapter that calls the runtime:

```python
from loop_runtime import TurnExecutor

executor = TurnExecutor(...)

async def live_agent(sample: Sample) -> tuple[str, float]:
    result = await executor.execute(input_text=sample.input, ...)
    return (result.output_text, result.cost_usd)
```

## 3. Deploying it

```sh
uv run loop deploy examples/support_agent --workspace ws_demo_001
```

The control plane will:

1. Build a deployable artefact.
2. Run the eval suite against the candidate (eval-gated deploy).
3. Promote to production only if pass rate ≥ baseline.
4. Wire the agent to its channels (`web-widget` by default).

## 4. Observing it

Every turn emits OTel spans that show up in your dashboards. The cost
dashboard at Studio's `/costs` page (see S027) breaks spend down per-agent
and per-metric over the current MTD window.
