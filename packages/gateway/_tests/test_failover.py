"""Tests for cross-provider failover in GatewayClient (vega #3)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from loop_gateway.client import GatewayClient
from loop_gateway.types import (
    GatewayDelta,
    GatewayDone,
    GatewayError,
    GatewayEvent,
    GatewayRequest,
    Provider,
    Usage,
)


class _StubProvider:
    """Test double that emits a scripted sequence of events."""

    def __init__(self, name: str, supports_models: tuple[str, ...], events: list[GatewayEvent]) -> None:
        self.name = name
        self._supports = supports_models
        self._events = events
        self.invocation_count = 0

    def supports(self, model: str) -> bool:
        return model in self._supports

    async def stream(self, request: GatewayRequest) -> AsyncIterator[GatewayEvent]:
        self.invocation_count += 1
        for event in self._events:
            yield event


def _request(model: str = "gpt-4o-mini") -> GatewayRequest:
    return GatewayRequest(
        model=model,
        workspace_id="00000000-0000-0000-0000-000000000001",
        request_id="rid-1",
        messages=(),
    )


@pytest.mark.asyncio
async def test_primary_provider_serves_when_clean() -> None:
    """No failover needed: primary streams a clean delta+done."""
    primary = _StubProvider(
        "openai-primary",
        ("gpt-4o-mini",),
        [GatewayDelta(text="hi"), GatewayDone(usage=Usage(input_tokens=10, output_tokens=2), cost_usd=0.0)],  # type: ignore[arg-type]
    )
    secondary = _StubProvider("openai-secondary", ("gpt-4o-mini",), [])
    client = GatewayClient([primary, secondary])  # type: ignore[list-item]
    events = [e async for e in client.stream(_request())]
    assert len(events) == 2
    assert primary.invocation_count == 1
    assert secondary.invocation_count == 0


@pytest.mark.asyncio
async def test_falls_over_on_retryable_provider_5xx() -> None:
    """Primary returns LOOP-GW-401 (5xx) before any token → secondary
    serves the request. Closes the per-vendor outage scenario."""
    primary = _StubProvider(
        "primary",
        ("gpt-4o-mini",),
        [GatewayError(code="LOOP-GW-401", message="provider 5xx")],
    )
    secondary = _StubProvider(
        "secondary",
        ("gpt-4o-mini",),
        [GatewayDelta(text="recovered"), GatewayDone(usage=Usage(input_tokens=10, output_tokens=2), cost_usd=0.0)],  # type: ignore[arg-type]
    )
    client = GatewayClient([primary, secondary])  # type: ignore[list-item]
    events = [e async for e in client.stream(_request())]
    # The primary's error event was discarded; only the secondary's
    # successful events reach the caller.
    assert len(events) == 2
    assert isinstance(events[0], GatewayDelta)
    assert events[0].text == "recovered"
    assert primary.invocation_count == 1
    assert secondary.invocation_count == 1


@pytest.mark.asyncio
async def test_falls_over_on_rate_limit() -> None:
    primary = _StubProvider(
        "primary",
        ("gpt-4o-mini",),
        [GatewayError(code="LOOP-GW-301", message="rate limit")],
    )
    secondary = _StubProvider(
        "secondary",
        ("gpt-4o-mini",),
        [GatewayDelta(text="ok"), GatewayDone(usage=Usage(input_tokens=10, output_tokens=2), cost_usd=0.0)],  # type: ignore[arg-type]
    )
    client = GatewayClient([primary, secondary])  # type: ignore[list-item]
    events = [e async for e in client.stream(_request())]
    assert len(events) == 2
    assert isinstance(events[0], GatewayDelta)


@pytest.mark.asyncio
async def test_does_not_fail_over_after_payload_emitted() -> None:
    """Once a token is yielded, we're committed — failing over after
    that would duplicate tokens or fork the assistant message."""
    primary = _StubProvider(
        "primary",
        ("gpt-4o-mini",),
        [
            GatewayDelta(text="hello"),
            GatewayError(code="LOOP-GW-401", message="mid-stream 5xx"),
        ],
    )
    secondary = _StubProvider(
        "secondary",
        ("gpt-4o-mini",),
        [GatewayDelta(text="should not appear"), GatewayDone(usage=Usage(input_tokens=10, output_tokens=2), cost_usd=0.0)],  # type: ignore[arg-type]
    )
    client = GatewayClient([primary, secondary])  # type: ignore[list-item]
    events = [e async for e in client.stream(_request())]
    # Caller sees primary's hello + the error. Secondary is NOT invoked.
    assert isinstance(events[0], GatewayDelta)
    assert events[0].text == "hello"
    assert isinstance(events[1], GatewayError)
    assert secondary.invocation_count == 0


@pytest.mark.asyncio
async def test_does_not_fail_over_on_non_retryable_error() -> None:
    """Auth failure (LOOP-GW-101) is NOT retryable: failing over to a
    different provider would still hit the same workspace-level auth
    issue (no BYO key)."""
    primary = _StubProvider(
        "primary",
        ("gpt-4o-mini",),
        [GatewayError(code="LOOP-GW-101", message="missing BYO key")],
    )
    secondary = _StubProvider(
        "secondary",
        ("gpt-4o-mini",),
        [GatewayDelta(text="x"), GatewayDone(usage=Usage(input_tokens=10, output_tokens=2), cost_usd=0.0)],  # type: ignore[arg-type]
    )
    client = GatewayClient([primary, secondary])  # type: ignore[list-item]
    events = [e async for e in client.stream(_request())]
    assert isinstance(events[0], GatewayError)
    assert events[0].code == "LOOP-GW-101"
    assert secondary.invocation_count == 0


@pytest.mark.asyncio
async def test_failover_exhausted_returns_structured_error() -> None:
    """All providers retry-error before any payload → structured
    LOOP-GW-403 'chain exhausted'."""
    primary = _StubProvider(
        "primary",
        ("gpt-4o-mini",),
        [GatewayError(code="LOOP-GW-401", message="primary 5xx")],
    )
    secondary = _StubProvider(
        "secondary",
        ("gpt-4o-mini",),
        [GatewayError(code="LOOP-GW-301", message="secondary rate limit")],
    )
    client = GatewayClient([primary, secondary])  # type: ignore[list-item]
    events = [e async for e in client.stream(_request())]
    assert len(events) == 1
    assert isinstance(events[0], GatewayError)
    # Either the last error or LOOP-GW-403 is acceptable
    assert events[0].code in ("LOOP-GW-301", "LOOP-GW-403")


@pytest.mark.asyncio
async def test_pick_chain_returns_supporting_providers_in_order() -> None:
    a = _StubProvider("a", ("gpt-4o",), [])
    b = _StubProvider("b", ("gpt-4o", "claude-3-haiku"), [])
    c = _StubProvider("c", ("claude-3-haiku",), [])
    client = GatewayClient([a, b, c])  # type: ignore[list-item]
    chain = client._pick_chain("gpt-4o")
    assert [p.name for p in chain] == ["a", "b"]
    chain = client._pick_chain("claude-3-haiku")
    assert [p.name for p in chain] == ["b", "c"]
    chain = client._pick_chain("unknown-model")
    assert chain == []
