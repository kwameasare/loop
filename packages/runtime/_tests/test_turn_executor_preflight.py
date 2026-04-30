"""Tests for the S029 budget pre-flight integration in TurnExecutor."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from loop.types import AgentEvent, ChannelType, ContentPart
from loop_gateway import (
    GatewayDelta,
    GatewayDone,
    GatewayEvent,
    GatewayRequest,
    Usage,
)
from loop_runtime import AgentConfig, TurnBudget, TurnExecutor


class _RecordingGateway:
    def __init__(self, events: list[GatewayEvent]) -> None:
        self._events = events
        self.requests_seen: list[GatewayRequest] = []

    async def stream(self, request: GatewayRequest) -> AsyncIterator[GatewayEvent]:
        self.requests_seen.append(request)
        for ev in self._events:
            yield ev


def _event() -> AgentEvent:
    return AgentEvent(
        workspace_id=uuid4(),
        conversation_id=uuid4(),
        user_id="u-1",
        channel=ChannelType.WEB,
        content=[ContentPart(type="text", text="hello")],
        received_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_preflight_swap_emits_degrade_and_uses_fallback_model() -> None:
    """Tight budget on an expensive primary -> swap to fallback, single degrade."""

    gw = _RecordingGateway(
        [
            GatewayDelta(text="ok"),
            GatewayDone(
                usage=Usage(input_tokens=10, output_tokens=5),
                cost_usd=0.001,
            ),
        ]
    )
    executor = TurnExecutor(gateway=gw)
    agent = AgentConfig(
        name="support",
        model="gpt-4o",  # expensive primary
        system_prompt="ROLE",
        budget=TurnBudget(
            max_cost_usd=0.05,
            max_iterations=1,
            max_output_tokens_per_iter=10_000,
            fallback_model="gpt-4o-mini",
        ),
    )
    out = [e async for e in executor.execute(agent, _event())]

    types = [e.type for e in out]
    # Pre-flight should have swapped models BEFORE the gateway call.
    assert "degrade" in types
    degrade_events = [e for e in out if e.type == "degrade"]
    assert len(degrade_events) == 1
    assert degrade_events[0].payload["reason"] == "budget_preflight_swap"
    assert degrade_events[0].payload["from_model"] == "gpt-4o"
    assert degrade_events[0].payload["to_model"] == "gpt-4o-mini"
    # And the actual gateway request must use the fallback.
    assert gw.requests_seen[0].model == "gpt-4o-mini"
    assert types[-1] == "complete"


@pytest.mark.asyncio
async def test_preflight_deny_emits_degrade_and_skips_gateway() -> None:
    """No fallback configured + estimate exceeds budget -> deny without calling gateway."""

    gw = _RecordingGateway(
        [GatewayDone(usage=Usage(input_tokens=0, output_tokens=0), cost_usd=0.0)]
    )
    executor = TurnExecutor(gateway=gw)
    agent = AgentConfig(
        name="support",
        model="gpt-4o",
        system_prompt="ROLE",
        budget=TurnBudget(
            max_cost_usd=0.0001,
            max_iterations=1,
            max_output_tokens_per_iter=10_000,
        ),
    )
    out = [e async for e in executor.execute(agent, _event())]

    types = [e.type for e in out]
    assert "degrade" in types
    degrade_events = [e for e in out if e.type == "degrade"]
    # Final degrade reason should be the preflight denial.
    assert any(e.payload.get("reason") == "budget_preflight" for e in degrade_events)
    # Critically, the gateway must NOT have been invoked.
    assert gw.requests_seen == []


@pytest.mark.asyncio
async def test_preflight_allow_passes_through_when_budget_fits() -> None:
    """Cheap model + generous budget -> allow, no degrade, primary model used."""

    gw = _RecordingGateway(
        [
            GatewayDelta(text="ok"),
            GatewayDone(
                usage=Usage(input_tokens=1, output_tokens=1),
                cost_usd=0.0001,
            ),
        ]
    )
    executor = TurnExecutor(gateway=gw)
    agent = AgentConfig(
        name="support",
        model="gpt-4o-mini",
        system_prompt="ROLE",
        budget=TurnBudget(
            max_cost_usd=1.00,
            max_iterations=1,
            max_output_tokens_per_iter=512,
            fallback_model="gpt-4o-mini",
        ),
    )
    out = [e async for e in executor.execute(agent, _event())]

    types = [e.type for e in out]
    assert "degrade" not in types
    assert gw.requests_seen[0].model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_preflight_swap_announces_only_once_across_iterations() -> None:
    """Multiple swap iterations -> exactly one degrade announcement."""

    gw = _RecordingGateway(
        [
            GatewayDelta(text="x"),
            GatewayDone(
                usage=Usage(input_tokens=1, output_tokens=1),
                cost_usd=0.001,
            ),
        ]
    )
    executor = TurnExecutor(gateway=gw)
    agent = AgentConfig(
        name="support",
        model="gpt-4o",
        system_prompt="R",
        budget=TurnBudget(
            max_cost_usd=0.05,
            max_iterations=1,  # only one iteration possible anyway
            max_output_tokens_per_iter=10_000,
            fallback_model="gpt-4o-mini",
        ),
    )
    out = [e async for e in executor.execute(agent, _event())]
    swap_events = [
        e
        for e in out
        if e.type == "degrade"
        and e.payload.get("reason") == "budget_preflight_swap"
    ]
    assert len(swap_events) == 1
