"""SSE cancellation propagation (vega #4).

When the HTTP client drops the connection mid-stream, ``stream_turn_sse``
must close the executor's async generator so we stop spending provider
quota for output the user will never see. These tests use a hand-rolled
executor double + a disconnect probe to assert the contract without a
real ASGI request."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID

import pytest
from loop.types import TurnEvent
from loop_data_plane._turns import RuntimeTurnRequest, stream_turn_sse
from loop_runtime import AgentConfig, TurnBudget

WORKSPACE_ID = UUID("11111111-1111-4111-8111-111111111111")
CONVERSATION_ID = UUID("22222222-2222-4222-8222-222222222222")


class _StubProbe:
    """Mimics ``starlette.requests.Request.is_disconnected``."""

    def __init__(self, *, disconnect_after: int) -> None:
        self._disconnect_after = disconnect_after
        self.calls = 0
        self.disconnected = False

    async def is_disconnected(self) -> bool:
        self.calls += 1
        if self.calls > self._disconnect_after:
            self.disconnected = True
        return self.disconnected


class _CountingExecutor:
    """Yields N TurnEvents, recording how many were actually pulled.

    We track ``aclose_called`` so tests can assert the executor's
    generator was closed (which is what releases upstream provider
    sockets) when the client disconnects."""

    def __init__(self, n: int) -> None:
        self._n = n
        self.events_yielded = 0
        self.aclose_called = False

    async def execute(
        self,
        _agent: AgentConfig,
        _event: object,
        *,
        request_id: str,
    ) -> AsyncIterator[TurnEvent]:
        try:
            for i in range(self._n):
                self.events_yielded += 1
                yield TurnEvent(
                    type="token",
                    payload={"text": f"tok-{i}"},
                    ts=datetime.now(UTC),
                )
                # Yield to the event loop so the consumer can run
                # the disconnect check between events.
                await asyncio.sleep(0)
        except GeneratorExit:
            self.aclose_called = True
            raise


def _request() -> RuntimeTurnRequest:
    return RuntimeTurnRequest(
        workspace_id=WORKSPACE_ID,
        conversation_id=CONVERSATION_ID,
        user_id="user-cancel",
        input="hello",
        request_id="turn-cancel",
        budget=TurnBudget(),
    )


@pytest.mark.asyncio
async def test_runs_to_completion_when_client_stays_connected() -> None:
    """Sanity: the disconnect plumbing doesn't break the happy path."""
    executor = _CountingExecutor(n=5)
    probe = _StubProbe(disconnect_after=999)
    chunks = [
        chunk async for chunk in stream_turn_sse(executor, _request(), request=probe)
    ]
    assert executor.events_yielded == 5
    assert not probe.disconnected
    # 5 delta frames + 1 final 'done' frame, plus per-event newlines.
    body = b"".join(chunks).decode()
    assert body.count("event: turn") == 5
    assert "event: done" in body


@pytest.mark.asyncio
async def test_stops_streaming_after_client_disconnect() -> None:
    """The executor must NOT be drained past the disconnect point."""
    executor = _CountingExecutor(n=20)
    probe = _StubProbe(disconnect_after=2)  # disconnect after 2 events
    chunks = [
        chunk async for chunk in stream_turn_sse(executor, _request(), request=probe)
    ]
    # The executor's loop yielded a few events before we noticed the
    # disconnect — that's fine, those events were already in flight.
    # The contract is: we don't drain ALL 20.
    assert executor.events_yielded < 20
    assert executor.events_yielded <= 4
    # The generator was closed (this is what releases upstream sockets).
    assert executor.aclose_called is True
    # No 'done' frame because the stream was cancelled, not completed.
    body = b"".join(chunks).decode()
    assert "event: done" not in body


@pytest.mark.asyncio
async def test_disconnect_probe_is_optional() -> None:
    """Existing call sites that don't pass a probe still work — this
    keeps the change backwards-compatible while we migrate callers."""
    executor = _CountingExecutor(n=3)
    chunks = [chunk async for chunk in stream_turn_sse(executor, _request())]
    assert executor.events_yielded == 3
    body = b"".join(chunks).decode()
    assert "event: done" in body


@pytest.mark.asyncio
async def test_clean_completion_does_not_raise_or_leak() -> None:
    """Smoke: the ``finally`` ``aclose`` is a no-op when the stream
    ends naturally (the generator has already returned), but it must
    not raise. This guards against a regression where the cleanup
    path swallows the original ``done`` frame."""
    executor = _CountingExecutor(n=2)
    chunks = [chunk async for chunk in stream_turn_sse(executor, _request())]
    body = b"".join(chunks).decode()
    assert "event: done" in body
    assert body.count("event: turn") == 2
