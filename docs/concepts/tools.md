# Tools

Tools are how an agent reaches into the outside world: function calls, MCP
servers, knowledge-base retrievals, and HTTP APIs. Loop normalises all of
these into a single `Tool` interface.

## Function tools

```python
from loop.sdk import tool

@tool
async def lookup_order(order_id: str) -> dict:
    return {"order_id": order_id, "status": "in_transit"}
```

The `@tool` decorator infers the JSON schema from the function's type hints,
generates an MCP server in-process, and registers it with the runtime. No
extra wiring needed.

## MCP tools

```python
from loop.sdk import Tool

tools = [
    Tool.mcp("loop-hub://kb@latest", kb_id="kb_demo_support"),
    Tool.mcp("github://", token="${GITHUB_TOKEN}"),
]
```

Anything with a public MCP endpoint can be mounted by URI. Secrets resolve
through the gateway's secret store at deploy time, never at definition
time.

## Tool execution

The runtime fans out tool calls in parallel, but enforces:

- a per-turn cap (`max_tool_calls_per_turn`)
- a per-call timeout
- structured `tool_call_start` / `tool_call_end` events for observability
- automatic redaction of secret-tagged arguments before they hit traces

See `packages/runtime/loop_runtime/turn_executor.py` for the dispatch
implementation.
