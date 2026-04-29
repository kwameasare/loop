"""Turn executor — the heart of the Loop runtime.

Owner: Founding Eng #1.
Companion: architecture/ARCHITECTURE.md §3.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, AsyncIterator
from uuid import uuid4

import structlog

from loop.types import AgentEvent, AgentResponse, TurnEvent

if TYPE_CHECKING:
    from loop.runtime.context import RuntimeContext
    from loop.sdk import Agent

logger = structlog.get_logger(__name__)


class TurnExecutor:
    """Executes one inbound turn for an agent.

    Reasoning loop:
      1. Load memory (user, session, scratch).
      2. Build prompt (system + memory + tool catalog + history + user msg).
      3. Stream LLM tokens; intercept structured tool calls.
      4. Dispatch tool calls in parallel via the MCP layer.
      5. Feed results back; iterate until terminal response, max_iterations, or budget exhaustion.
      6. Persist memory diff. Flush trace.

    Invariants:
      - Budget-bounded: never exceeds max_cost_usd, max_iterations, max_runtime_seconds.
      - Idempotent: the same `event` retried produces the same observable result.
      - Streaming-first: emits tokens & tool events as they happen, not at the end.
      - Observable: every step emits an OTel span with cost + latency attrs.
    """

    def __init__(self, ctx: "RuntimeContext") -> None:
        self.ctx = ctx

    async def execute(
        self,
        agent: "Agent",
        event: AgentEvent,
        ctx: "RuntimeContext",
    ) -> AsyncIterator[TurnEvent]:
        turn_id = uuid4()
        started = time.monotonic()
        log = logger.bind(turn_id=str(turn_id), agent=agent.name, channel=event.channel.value)
        log.info("turn.start")

        memory = await ctx.memory.load(event)
        prompt = ctx.prompt_builder.build(agent, memory, event)

        cost_usd = 0.0
        iteration = 0
        final_response: AgentResponse | None = None

        async for chunk in ctx.gateway.stream(
            model=agent.model,
            prompt=prompt,
            tools=ctx.tools.catalog_for(agent),
            request_id=str(turn_id),
        ):
            cost_usd += chunk.cost_delta_usd

            if self._over_budget(agent, cost_usd, started, iteration):
                yield TurnEvent(
                    type="degrade",
                    payload={"reason": "budget", "cost_usd": cost_usd},
                    ts=ctx.clock.now(),
                )
                break

            if chunk.tool_call is not None:
                yield TurnEvent(
                    type="tool_call",
                    payload={"name": chunk.tool_call.name, "phase": "start"},
                    ts=ctx.clock.now(),
                )
                result = await ctx.tools.dispatch(chunk.tool_call, agent=agent, turn_id=turn_id)
                cost_usd += result.cost_usd
                yield TurnEvent(
                    type="tool_call",
                    payload={"name": chunk.tool_call.name, "phase": "end", "ok": result.error is None},
                    ts=ctx.clock.now(),
                )
                ctx.gateway.feed_tool_result(chunk.tool_call.name, result)
                iteration += 1
                continue

            if chunk.text is not None:
                yield TurnEvent(type="token", payload={"text": chunk.text}, ts=ctx.clock.now())

            if chunk.is_terminal:
                final_response = AgentResponse(
                    conversation_id=event.conversation_id,
                    content=chunk.final_content or [],
                    end_turn=True,
                )
                break

        await ctx.memory.persist_diff(event, memory)
        await ctx.trace.flush(turn_id)

        latency_ms = int((time.monotonic() - started) * 1000)
        log.info("turn.done", latency_ms=latency_ms, cost_usd=cost_usd, iters=iteration)

        yield TurnEvent(
            type="complete",
            payload=(final_response or AgentResponse(
                conversation_id=event.conversation_id, content=[], end_turn=True
            )).model_dump(mode="json"),
            ts=ctx.clock.now(),
        )

    def _over_budget(self, agent: "Agent", cost_usd: float, started: float, iteration: int) -> bool:
        if cost_usd >= agent.max_cost_usd:
            return True
        if iteration >= agent.max_iterations:
            return True
        if (time.monotonic() - started) >= agent.max_runtime_seconds:
            return True
        return False
