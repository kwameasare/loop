# Agents

A Loop agent is a Python class that subclasses `loop.sdk.Agent`. It bundles
**instructions**, **tools**, **memory configuration**, and **hard caps** into
a single deployable unit.

```python
from loop.sdk import Agent, Memory, Tool

class SupportAgent(Agent):
    name = "support-en"
    model = "claude-sonnet-4-7"
    instructions = "You are a friendly support agent..."
    tools = [Tool.fn(lookup_order)]
    memory = Memory(user="postgres", session=Memory.ttl("24h"))
    max_iterations = 6
    max_cost_usd = 0.10
```

## The reasoning loop

Each inbound message runs through `TurnExecutor.execute()`, which:

1. Loads the agent's memory tiers for the conversation.
2. Sends the prompt + tool schema to the gateway.
3. Streams `TurnEvent`s as deltas land.
4. Dispatches tool calls in parallel; emits `tool_call_start` / `tool_call_end`.
5. Optionally loops (up to `max_iterations`) if the model requested more tools.
6. Checks the budget every iteration; emits `degrade` and either swaps to a
   cheaper model or terminates.
7. Persists memory diffs and emits `complete`.

## Hard caps

Every loop iteration consults `_over_budget`. The five caps are:

| Cap | Default | Purpose |
| --- | --- | --- |
| `max_iterations` | 8 | tool-call ping-pong ceiling |
| `max_cost_usd` | 0.10 | per-turn USD ceiling |
| `max_runtime_seconds` | 30 | wall-clock ceiling |
| `max_tool_calls_per_turn` | 16 | denial-of-service guard |
| `max_message_bytes` | 32_768 | runaway-prompt guard |

See [engineering/PERFORMANCE.md](../../loop_implementation/engineering/PERFORMANCE.md)
for the full rationale.
