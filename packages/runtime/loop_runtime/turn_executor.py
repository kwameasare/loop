"""TurnExecutor v1 -- multi-iteration reasoning loop with parallel tool dispatch.

The executor walks an inbound :class:`AgentEvent` through one or more LLM
calls, dispatching every tool call the model emits in parallel, then
re-streaming with the tool results appended until the model is done or the
budget is exhausted (story S012).

Iteration shape per turn::

    [system, user]                                # iteration 0 prompt
        -> stream tokens -> GatewayDone(tool_calls=[T1, T2])
        -> dispatch T1, T2 in parallel
    [..., assistant(tool_calls=[T1,T2]), tool(T1), tool(T2)]
        -> stream tokens -> GatewayDone(tool_calls=())
    => emit `complete`

Invariants (still held from v0):
  * **Budget-bounded** -- ``budget.max_cost_usd`` and
    ``budget.max_runtime_seconds`` are checked at every event boundary;
    breach emits a ``degrade`` frame and ends the turn.
  * **Idempotent** -- per-iteration ``request_id`` is derived
    deterministically from the turn's ``request_id`` so retries hit the
    gateway cache.
  * **Streaming-first** -- token frames are forwarded as upstream deltas
    arrive; tool dispatch never buffers an entire iteration.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

import structlog
from loop.observability import tracer
from loop.types import AgentEvent, AgentResponse, ContentPart, TurnEvent
from loop_gateway import (
    GatewayDelta,
    GatewayDone,
    GatewayError,
    GatewayEvent,
    GatewayMessage,
    GatewayRequest,
    ToolCall,
    ToolSpec,
)
from pydantic import BaseModel, ConfigDict, Field

logger = structlog.get_logger(__name__)


class ToolRegistryLike(Protocol):
    """A tool registry the executor can describe to the model and call.

    Defined as a Protocol so the runtime does not import ``loop_mcp``;
    keeps the dependency arrow pointing the right way.
    """

    def describe_specs(self) -> list[ToolSpec]: ...
    async def call(self, name: str, arguments: dict[str, Any]) -> Any: ...


class TurnBudget(BaseModel):
    """Per-turn limits. Breach emits a ``degrade`` frame and ends the turn."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_cost_usd: float = Field(default=0.50, gt=0)
    max_runtime_seconds: float = Field(default=30.0, gt=0)
    max_iterations: int = Field(default=4, ge=1)


class AgentConfig(BaseModel):
    """Minimal agent surface the executor needs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    model: str
    system_prompt: str = ""
    budget: TurnBudget = Field(default_factory=TurnBudget)


class GatewayLike(Protocol):
    """Subset of the gateway client the executor calls."""

    def stream(self, request: GatewayRequest) -> AsyncIterator[GatewayEvent]: ...


def _now() -> datetime:
    return datetime.now(UTC)


def _initial_messages(agent: AgentConfig, event: AgentEvent) -> list[GatewayMessage]:
    out: list[GatewayMessage] = []
    if agent.system_prompt:
        out.append(GatewayMessage(role="system", content=agent.system_prompt))
    user_text = "\n".join(
        part.text for part in event.content if part.type == "text" and part.text
    )
    if user_text:
        out.append(GatewayMessage(role="user", content=user_text))
    return out


def _stringify(result: Any) -> str:
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result, default=str)
    except (TypeError, ValueError):
        return repr(result)


async def _dispatch_tool(
    registry: ToolRegistryLike, call: ToolCall
) -> tuple[ToolCall, str, str | None]:
    """Run one tool call. Returns (call, result_str, error_str_or_None)."""

    try:
        result = await registry.call(call.name, dict(call.arguments))
    except Exception as exc:
        return call, "", f"{type(exc).__name__}: {exc}"
    return call, _stringify(result), None


class TurnExecutor:
    """Multi-iteration executor; dispatches tool calls in parallel each iteration."""

    def __init__(self, gateway: GatewayLike) -> None:
        self._gateway = gateway

    async def execute(
        self,
        agent: AgentConfig,
        event: AgentEvent,
        *,
        request_id: str | None = None,
        tools: ToolRegistryLike | None = None,
    ) -> AsyncIterator[TurnEvent]:
        turn_id = uuid4()
        base_request_id = request_id or str(turn_id)
        started = time.monotonic()
        log = logger.bind(
            turn_id=str(turn_id),
            agent=agent.name,
            workspace_id=str(event.workspace_id),
        )
        log.info("turn.start")

        messages = _initial_messages(agent, event)
        tool_specs: tuple[ToolSpec, ...] = (
            tuple(tools.describe_specs()) if tools is not None else ()
        )
        accumulated_text: list[str] = []
        cost_usd = 0.0
        degrade_reason: str | None = None
        pending_tool_calls: tuple[ToolCall, ...] = ()

        with tracer.span(
            "turn.execute",
            kind="llm",
            attrs={
                "workspace_id": str(event.workspace_id),
                "conversation_id": str(event.conversation_id),
                "turn_id": str(turn_id),
                "agent_id": agent.name,
                "model": agent.model,
            },
        ) as span:
            iterations_used = 0
            for iteration in range(agent.budget.max_iterations):
                iterations_used = iteration + 1
                if time.monotonic() - started >= agent.budget.max_runtime_seconds:
                    degrade_reason = "timeout"
                    break
                # Symmetric with the timeout guard: don't START a new iteration
                # if the cost budget is already exhausted by prior iterations.
                # The mid-stream check at line ~210 handles overshoot inside
                # the current iteration; this prevents one extra iteration
                # from being launched after a prior one tipped over.
                if cost_usd >= agent.budget.max_cost_usd:
                    degrade_reason = "budget"
                    break

                gw_request = GatewayRequest(
                    request_id=f"{base_request_id}:i{iteration}",
                    workspace_id=str(event.workspace_id),
                    model=agent.model,
                    messages=tuple(messages),
                    tools=tool_specs,
                )

                pending_tool_calls = ()
                async for gw_event in self._gateway.stream(gw_request):
                    if time.monotonic() - started >= agent.budget.max_runtime_seconds:
                        degrade_reason = "timeout"
                        break
                    if isinstance(gw_event, GatewayDelta):
                        accumulated_text.append(gw_event.text)
                        yield TurnEvent(
                            type="token",
                            payload={"text": gw_event.text},
                            ts=_now(),
                        )
                    elif isinstance(gw_event, GatewayDone):
                        cost_usd += gw_event.cost_usd
                        span.set_attr("input_tokens", gw_event.usage.input_tokens)
                        span.set_attr("output_tokens", gw_event.usage.output_tokens)
                        pending_tool_calls = gw_event.tool_calls
                        if cost_usd > agent.budget.max_cost_usd:
                            degrade_reason = "budget"
                        break
                    elif isinstance(gw_event, GatewayError):
                        degrade_reason = f"gateway:{gw_event.code}"
                        span.record_error_code(gw_event.code)
                        break

                if degrade_reason is not None or not pending_tool_calls:
                    break

                if tools is None:
                    # Model asked for tools we never advertised -- protocol
                    # violation; degrade rather than silently dropping calls.
                    degrade_reason = "tool_calls_without_registry"
                    break

                messages.append(
                    GatewayMessage(
                        role="assistant",
                        content="",
                        tool_calls=pending_tool_calls,
                    )
                )

                for c in pending_tool_calls:
                    yield TurnEvent(
                        type="tool_call",
                        payload={
                            "id": c.id,
                            "name": c.name,
                            "arguments": dict(c.arguments),
                        },
                        ts=_now(),
                    )

                # Parallel dispatch -- one slow tool does not block the others.
                results = await asyncio.gather(
                    *(_dispatch_tool(tools, c) for c in pending_tool_calls)
                )
                for call, result_str, err in results:
                    yield TurnEvent(
                        type="tool_result",
                        payload={
                            "id": call.id,
                            "name": call.name,
                            "result": result_str,
                            "error": err,
                        },
                        ts=_now(),
                    )
                    messages.append(
                        GatewayMessage(
                            role="tool",
                            content=result_str if err is None else f"ERROR: {err}",
                            tool_call_id=call.id,
                            name=call.name,
                        )
                    )

            # Loop exited. If we hit max_iterations with calls still pending
            # and no other degrade reason, mark it.
            if (
                degrade_reason is None
                and pending_tool_calls
                and iterations_used >= agent.budget.max_iterations
            ):
                degrade_reason = "max_iterations"

            span.set_attr("cost_usd", cost_usd)
            span.set_attr("loop.turn.iterations", iterations_used)
            if degrade_reason is not None:
                span.set_attr("loop.turn.degrade_reason", degrade_reason)

        if degrade_reason is not None:
            yield TurnEvent(
                type="degrade",
                payload={"reason": degrade_reason, "cost_usd": cost_usd},
                ts=_now(),
            )

        response = self._materialize_response(event.conversation_id, accumulated_text)
        yield TurnEvent(
            type="complete", payload=response.model_dump(mode="json"), ts=_now()
        )

        latency_ms = int((time.monotonic() - started) * 1000)
        log.info(
            "turn.done",
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            degrade=degrade_reason,
            iterations=iterations_used,
        )

    @staticmethod
    def _materialize_response(
        conversation_id: UUID, parts: list[str]
    ) -> AgentResponse:
        text = "".join(parts)
        content = [ContentPart(type="text", text=text)] if text else []
        return AgentResponse(
            conversation_id=conversation_id, content=content, end_turn=True
        )


__all__ = [
    "AgentConfig",
    "GatewayLike",
    "ToolRegistryLike",
    "TurnBudget",
    "TurnExecutor",
]
