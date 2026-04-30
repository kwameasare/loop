"""TurnExecutor v0 tests with a fake gateway."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from loop.types import AgentEvent, ChannelType, ContentPart
from loop_gateway import (
    GatewayDelta,
    GatewayDone,
    GatewayError,
    GatewayEvent,
    GatewayRequest,
    Usage,
)
from loop_runtime import AgentConfig, TurnBudget, TurnExecutor


class _FakeGateway:
    """Yields a scripted sequence; records the request seen for assertions."""

    def __init__(self, events: list[GatewayEvent]) -> None:
        self.events = events
        self.last_request: GatewayRequest | None = None

    async def stream(self, request: GatewayRequest) -> AsyncIterator[GatewayEvent]:
        self.last_request = request
        for ev in self.events:
            yield ev


def _event(text: str = "hello") -> AgentEvent:
    return AgentEvent(
        workspace_id=uuid4(),
        conversation_id=uuid4(),
        user_id="u-1",
        channel=ChannelType.WEB,
        content=[ContentPart(type="text", text=text)],
        received_at=datetime.now(UTC),
    )


def _agent(system: str = "be terse", budget: TurnBudget | None = None) -> AgentConfig:
    return AgentConfig(
        name="support",
        model="gpt-4o-mini",
        system_prompt=system,
        budget=budget or TurnBudget(),
    )


@pytest.mark.asyncio
async def test_streams_tokens_then_complete() -> None:
    gw = _FakeGateway(
        [
            GatewayDelta(text="Hi"),
            GatewayDelta(text=" there"),
            GatewayDone(usage=Usage(input_tokens=5, output_tokens=2), cost_usd=0.01),
        ]
    )
    executor = TurnExecutor(gateway=gw)
    out = [e async for e in executor.execute(_agent(), _event())]

    types = [e.type for e in out]
    assert types == ["token", "token", "complete"]
    assert [e.payload["text"] for e in out if e.type == "token"] == ["Hi", " there"]

    final = out[-1]
    assert final.type == "complete"
    assert final.payload["content"][0]["text"] == "Hi there"
    assert final.payload["end_turn"] is True


@pytest.mark.asyncio
async def test_request_includes_system_and_user_messages() -> None:
    gw = _FakeGateway(
        [GatewayDone(usage=Usage(input_tokens=0, output_tokens=0), cost_usd=0.0)]
    )
    executor = TurnExecutor(gateway=gw)
    [_ async for _ in executor.execute(_agent(system="ROLE"), _event(text="ping"))]

    assert gw.last_request is not None
    roles = [m.role for m in gw.last_request.messages]
    contents = [m.content for m in gw.last_request.messages]
    assert roles == ["system", "user"]
    assert contents == ["ROLE", "ping"]


@pytest.mark.asyncio
async def test_request_id_overrides_default() -> None:
    gw = _FakeGateway(
        [GatewayDone(usage=Usage(input_tokens=0, output_tokens=0), cost_usd=0.0)]
    )
    executor = TurnExecutor(gateway=gw)
    [
        _
        async for _ in executor.execute(_agent(), _event(), request_id="caller-pinned-id")
    ]
    assert gw.last_request is not None
    assert gw.last_request.request_id == "caller-pinned-id"


@pytest.mark.asyncio
async def test_workspace_id_propagates_to_gateway_request() -> None:
    """No cross-workspace leak: the executor must pass the inbound event's workspace_id."""
    gw = _FakeGateway(
        [GatewayDone(usage=Usage(input_tokens=0, output_tokens=0), cost_usd=0.0)]
    )
    executor = TurnExecutor(gateway=gw)
    event = _event()
    [_ async for _ in executor.execute(_agent(), event)]
    assert gw.last_request is not None
    assert gw.last_request.workspace_id == str(event.workspace_id)


@pytest.mark.asyncio
async def test_emits_degrade_when_done_cost_exceeds_budget() -> None:
    gw = _FakeGateway(
        [
            GatewayDelta(text="ok"),
            GatewayDone(usage=Usage(input_tokens=10, output_tokens=10), cost_usd=99.0),
        ]
    )
    executor = TurnExecutor(gateway=gw)
    out = [
        e
        async for e in executor.execute(
            _agent(budget=TurnBudget(max_cost_usd=0.10)), _event()
        )
    ]
    types = [e.type for e in out]
    assert "degrade" in types
    degrade = next(e for e in out if e.type == "degrade")
    assert degrade.payload["reason"] == "budget"
    assert types[-1] == "complete"  # turn always terminates with complete


@pytest.mark.asyncio
async def test_gateway_error_emits_degrade_then_complete() -> None:
    gw = _FakeGateway([GatewayError(code="GW-PARSE", message="bad json")])
    executor = TurnExecutor(gateway=gw)
    out = [e async for e in executor.execute(_agent(), _event())]
    types = [e.type for e in out]
    assert types == ["degrade", "complete"]
    assert out[0].payload["reason"].startswith("gateway:GW-PARSE")


@pytest.mark.asyncio
async def test_emits_otel_span_with_required_attrs() -> None:
    from loop.observability import reset_for_test

    exporter = reset_for_test()
    gw = _FakeGateway(
        [
            GatewayDelta(text="hi"),
            GatewayDone(usage=Usage(input_tokens=7, output_tokens=3), cost_usd=0.02),
        ]
    )
    executor = TurnExecutor(gateway=gw)
    event = _event()
    [_ async for _ in executor.execute(_agent(), event)]

    finished = exporter.get_finished_spans()
    assert len(finished) == 1
    span = finished[0]
    assert span.name == "turn.execute"
    attrs = dict(span.attributes or {})
    assert attrs["loop.span.kind"] == "llm"
    assert attrs["workspace_id"] == str(event.workspace_id)
    assert attrs["conversation_id"] == str(event.conversation_id)
    assert attrs["agent_id"] == "support"
    assert attrs["model"] == "gpt-4o-mini"
    assert attrs["input_tokens"] == 7
    assert attrs["output_tokens"] == 3
    assert attrs["cost_usd"] == pytest.approx(0.02)
