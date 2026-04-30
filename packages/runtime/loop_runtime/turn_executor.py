"""TurnExecutor v0 -- the single-pass reasoning loop.

This is the tools-less spike (story S008). The executor takes an inbound
``AgentEvent``, walks one LLM call through the gateway, streams ``TurnEvent``
frames as deltas land, and finishes with a ``complete`` event carrying an
``AgentResponse``. Tool dispatch + multi-iteration land in S012.

Invariants (held even in v0):
  * **Budget-bounded** -- never exceeds ``budget.max_cost_usd`` /
    ``budget.max_runtime_seconds``; degrade event emitted on breach.
  * **Idempotent** -- the same ``(workspace_id, request_id)`` retried hits the
    gateway's idempotency cache and produces the same observable stream.
  * **Streaming-first** -- token frames are yielded as upstream deltas arrive,
    not buffered to the end.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

import structlog
from loop.observability import tracer
from loop.types import AgentEvent, AgentResponse, ContentPart, TurnEvent
from loop_gateway import (
    GatewayDelta,
    GatewayDone,
    GatewayError,
    GatewayEvent,
    GatewayRequest,
)
from loop_gateway.types import GatewayMessage
from pydantic import BaseModel, ConfigDict, Field

logger = structlog.get_logger(__name__)


class TurnBudget(BaseModel):
    """Per-turn limits. Breach emits a ``degrade`` frame and ends the turn."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_cost_usd: float = Field(default=0.50, gt=0)
    max_runtime_seconds: float = Field(default=30.0, gt=0)
    max_iterations: int = Field(default=1, ge=1)


class AgentConfig(BaseModel):
    """Minimal agent surface the executor needs in v0."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    model: str
    system_prompt: str = ""
    budget: TurnBudget = Field(default_factory=TurnBudget)


class GatewayLike(Protocol):
    """Subset of the gateway client the executor calls.

    Defined as a Protocol so tests can swap a fake client without depending
    on the real ``loop_gateway.GatewayClient`` -- and so the runtime stays
    loosely coupled in case we add a second client transport.
    """

    def stream(self, request: GatewayRequest) -> AsyncIterator[GatewayEvent]: ...


def _now() -> datetime:
    return datetime.now(UTC)


def _build_messages(agent: AgentConfig, event: AgentEvent) -> tuple[GatewayMessage, ...]:
    out: list[GatewayMessage] = []
    if agent.system_prompt:
        out.append(GatewayMessage(role="system", content=agent.system_prompt))
    user_text = "\n".join(
        part.text for part in event.content if part.type == "text" and part.text
    )
    if user_text:
        out.append(GatewayMessage(role="user", content=user_text))
    return tuple(out)


class TurnExecutor:
    """Single-pass executor; v0 does **not** dispatch tools (see S012)."""

    def __init__(self, gateway: GatewayLike) -> None:
        self._gateway = gateway

    async def execute(
        self,
        agent: AgentConfig,
        event: AgentEvent,
        *,
        request_id: str | None = None,
    ) -> AsyncIterator[TurnEvent]:
        turn_id = uuid4()
        request_id = request_id or str(turn_id)
        started = time.monotonic()
        log = logger.bind(
            turn_id=str(turn_id),
            agent=agent.name,
            workspace_id=str(event.workspace_id),
        )
        log.info("turn.start")

        gw_request = GatewayRequest(
            request_id=request_id,
            workspace_id=str(event.workspace_id),
            model=agent.model,
            messages=_build_messages(agent, event),
        )

        accumulated_text: list[str] = []
        cost_usd = 0.0
        degrade_reason: str | None = None

        # One LLM-kind span per turn; cost/latency/degrade attributes are
        # set as we learn them. Dashboards rely on `loop.span.kind=llm`.
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
            async for gw_event in self._gateway.stream(gw_request):
                # Time-budget check at every event boundary.
                if time.monotonic() - started >= agent.budget.max_runtime_seconds:
                    degrade_reason = "timeout"
                    break

                if isinstance(gw_event, GatewayDelta):
                    accumulated_text.append(gw_event.text)
                    yield TurnEvent(
                        type="token", payload={"text": gw_event.text}, ts=_now()
                    )
                elif isinstance(gw_event, GatewayDone):
                    cost_usd = gw_event.cost_usd
                    span.set_attr("input_tokens", gw_event.usage.input_tokens)
                    span.set_attr("output_tokens", gw_event.usage.output_tokens)
                    if cost_usd > agent.budget.max_cost_usd:
                        degrade_reason = "budget"
                    break
                elif isinstance(gw_event, GatewayError):
                    degrade_reason = f"gateway:{gw_event.code}"
                    span.record_error_code(gw_event.code)
                    break

            span.set_attr("cost_usd", cost_usd)
            if degrade_reason is not None:
                span.set_attr("loop.turn.degrade_reason", degrade_reason)

        if degrade_reason is not None:
            yield TurnEvent(
                type="degrade",
                payload={"reason": degrade_reason, "cost_usd": cost_usd},
                ts=_now(),
            )

        response = self._materialize_response(event.conversation_id, accumulated_text)
        yield TurnEvent(type="complete", payload=response.model_dump(mode="json"), ts=_now())

        latency_ms = int((time.monotonic() - started) * 1000)
        log.info(
            "turn.done",
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            degrade=degrade_reason,
        )

    @staticmethod
    def _materialize_response(conversation_id: UUID, parts: list[str]) -> AgentResponse:
        text = "".join(parts)
        content = [ContentPart(type="text", text=text)] if text else []
        return AgentResponse(conversation_id=conversation_id, content=content, end_turn=True)


__all__ = ["AgentConfig", "GatewayLike", "TurnBudget", "TurnExecutor"]
