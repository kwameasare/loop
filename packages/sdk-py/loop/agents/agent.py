"""Public Agent base class. The single most important type in the SDK."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

from loop.types import AgentEvent, AgentResponse, ContentPart, TurnEvent

if TYPE_CHECKING:
    from loop.context import Context
    from loop.memory import Memory
    from loop.tools import Tool


class Agent(ABC):
    """Base class for a Loop agent.

    Subclass and set `name`, `model`, `instructions`. Optional class attributes:
    `tools`, `memory`, `max_iterations`, `max_cost_usd`, `max_runtime_seconds`.

    Implement `on_message` for full control, or use `act()` for the standard
    reasoning loop.

    Example:
        class SupportAgent(Agent):
            name = "support"
            model = "claude-sonnet-4-7"
            instructions = "You help customers resolve order issues."
            tools = [Tool.mcp("loop-hub://stripe@1.4")]

            async def on_message(self, msg, ctx):
                return await self.act(msg, ctx)
    """

    name: ClassVar[str]
    model: ClassVar[str]
    instructions: ClassVar[str]

    tools: ClassVar[list[Tool]] = []
    memory: ClassVar[Memory | None] = None

    max_iterations: ClassVar[int] = 10
    max_cost_usd: ClassVar[float] = 0.50
    max_runtime_seconds: ClassVar[int] = 300
    max_tool_calls_per_turn: ClassVar[int] = 20

    @abstractmethod
    async def on_message(self, event: AgentEvent, ctx: Context) -> AgentResponse: ...

    async def act(self, event: AgentEvent, ctx: Context) -> AgentResponse:
        """Run the standard reasoning loop until termination.

        Streams `TurnEvent`s through `ctx.emit(...)`; returns the final response.
        """
        executor = ctx.runtime.turn_executor
        events: list[TurnEvent] = []
        async for ev in executor.execute(self, event, ctx):
            events.append(ev)
            await ctx.emit(ev)
        # The final TurnEvent of type "complete" carries the AgentResponse.
        for ev in reversed(events):
            if ev.type == "complete":
                return AgentResponse.model_validate(ev.payload)
        return AgentResponse(
            conversation_id=event.conversation_id,
            content=[ContentPart(type="text", text="...")],
            end_turn=True,
        )
