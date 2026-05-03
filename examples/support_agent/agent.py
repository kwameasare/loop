"""Reference example: a simple customer-support agent.

The class is a thin subclass of :class:`loop.agents.Agent` exposing the
agent's static configuration (name, model, instructions, caps). The
runnable wiring against the real gateway lives in ``run_local.py`` so
the example file stays declarative.

Run locally (real LLM, real ``lookup_order`` tool call)::

    uv run python examples/support_agent/run_local.py "where is order 4172?"
"""

from __future__ import annotations

from typing import Any, ClassVar

from loop.agents import Agent
from loop.types import AgentEvent, AgentResponse, ContentPart


async def lookup_order(order_id: str) -> dict[str, Any]:
    """Look up an order by ID. Returns status + estimated delivery.

    Replace with a real API call in production; this example uses a
    deterministic fixture so the LLM-tool round-trip is reproducible.
    """

    return {
        "order_id": order_id,
        "status": "in_transit",
        "estimated_delivery": "2026-05-02",
    }


LOOKUP_ORDER_TOOL_SCHEMA: dict[str, Any] = {
    "name": "lookup_order",
    "description": "Look up an order by ID. Returns status + estimated delivery.",
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "Customer-facing order identifier, e.g. '4172'.",
            }
        },
        "required": ["order_id"],
    },
}


class SupportAgent(Agent):
    """Customer-support agent definition.

    The class is intentionally declarative: ``run_local.py`` wires it to a
    real gateway provider. Tests substitute a fake provider by passing it
    to :func:`run_local.run_turn`.
    """

    name: ClassVar[str] = "support-en"
    model: ClassVar[str] = "gpt-4o-mini"

    instructions: ClassVar[str] = (
        "You are a friendly customer support agent for an online retailer.\n"
        "- Use lookup_order when the user asks about an order.\n"
        '- If you don\'t know, say "I don\'t know" and offer to escalate.\n'
        "- Never invent order details."
    )

    max_iterations: ClassVar[int] = 6
    max_cost_usd: ClassVar[float] = 0.10

    async def on_message(self, event: AgentEvent, ctx: object) -> AgentResponse:
        # The real reasoning loop lives in ``run_local.run_turn`` so the
        # example runs without a full runtime context wired up.
        return AgentResponse(
            conversation_id=event.conversation_id,
            content=[ContentPart(type="text", text="see run_local.run_turn")],
            end_turn=True,
        )


__all__ = ["LOOKUP_ORDER_TOOL_SCHEMA", "SupportAgent", "lookup_order"]
