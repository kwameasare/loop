"""Reference example: a simple customer-support agent.

Run locally:
    uv run loop dev examples/support_agent
"""

from __future__ import annotations

from loop.sdk import Agent, Memory, Tool, tool
from loop.types import AgentEvent, AgentResponse


@tool
async def lookup_order(order_id: str) -> dict:
    """Look up an order by ID. Returns status + estimated delivery."""
    # Replace with a real API call. The decorator turns this into an in-process MCP server.
    return {
        "order_id": order_id,
        "status": "in_transit",
        "estimated_delivery": "2026-05-02",
    }


class SupportAgent(Agent):
    name = "support-en"
    model = "claude-sonnet-4-7"

    instructions = """\
You are a friendly customer support agent for an online retailer.
- Use lookup_order when the user asks about an order.
- If you don't know, say "I don't know" and offer to escalate.
- Never invent order details.
"""

    tools = [
        Tool.fn(lookup_order),
        Tool.mcp("loop-hub://kb@latest", kb_id="${SUPPORT_KB_ID}"),
    ]

    memory = Memory(
        user="postgres",
        session=Memory.ttl("24h"),
        scratch=Memory.in_run(),
    )

    max_iterations = 6
    max_cost_usd = 0.10

    async def on_message(self, event: AgentEvent, ctx) -> AgentResponse:
        return await self.act(event, ctx)
