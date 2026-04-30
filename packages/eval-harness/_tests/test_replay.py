"""Tests for production-replay capture (S026)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from loop_eval import (
    FailedTurn,
    InMemoryReplaySink,
    capture,
    should_capture,
    to_samples,
)


def _turn(request_id: str = "req-1", **kw: object) -> FailedTurn:
    return FailedTurn(
        workspace_id=kw.get("workspace_id", uuid4()),  # type: ignore[arg-type]
        agent_id=kw.get("agent_id", uuid4()),  # type: ignore[arg-type]
        request_id=request_id,
        input_text=kw.get("input_text", "hi please help"),  # type: ignore[arg-type]
        output_text=kw.get("output_text", "i can't"),  # type: ignore[arg-type]
        failure_reason=kw.get("failure_reason", "max_iterations"),  # type: ignore[arg-type]
        timestamp_ms=kw.get("timestamp_ms", 12345),  # type: ignore[arg-type]
    )


def test_should_capture_deterministic_for_same_key() -> None:
    ws = uuid4()
    a = should_capture(workspace_id=ws, request_id="r1", sample_rate=0.5)
    b = should_capture(workspace_id=ws, request_id="r1", sample_rate=0.5)
    assert a == b


def test_should_capture_extremes() -> None:
    ws = uuid4()
    assert should_capture(workspace_id=ws, request_id="x", sample_rate=0.0) is False
    assert should_capture(workspace_id=ws, request_id="x", sample_rate=1.0) is True


def test_should_capture_rate_distributes() -> None:
    ws = uuid4()
    captured = sum(
        1
        for i in range(1000)
        if should_capture(workspace_id=ws, request_id=f"r{i}", sample_rate=0.25)
    )
    assert 200 < captured < 300


@pytest.mark.asyncio
async def test_capture_appends_when_sampled() -> None:
    sink = InMemoryReplaySink()
    turn = _turn()
    appended = await capture(sink=sink, turn=turn, sample_rate=1.0)
    assert appended is True
    assert (await sink.list()) == [turn]


@pytest.mark.asyncio
async def test_capture_skips_when_not_sampled() -> None:
    sink = InMemoryReplaySink()
    turn = _turn()
    appended = await capture(sink=sink, turn=turn, sample_rate=0.0)
    assert appended is False
    assert (await sink.list()) == []


@pytest.mark.asyncio
async def test_capture_applies_redactor() -> None:
    sink = InMemoryReplaySink()
    turn = _turn(input_text="my email is a@b.test", output_text="ok")
    await capture(
        sink=sink,
        turn=turn,
        sample_rate=1.0,
        redactor=lambda s: s.replace("a@b.test", "<email>"),
    )
    items = await sink.list()
    assert items[0].input_text == "my email is <email>"
    assert items[0].output_text == "ok"


def test_to_samples_carries_metadata() -> None:
    turn = _turn(failure_reason="tool_error")
    samples = to_samples([turn])
    assert len(samples) == 1
    s = samples[0]
    assert s.id == f"replay-{turn.request_id}"
    assert s.input == turn.input_text
    assert s.expected == turn.output_text
    assert s.metadata["failure_reason"] == "tool_error"
    assert s.metadata["workspace_id"] == str(turn.workspace_id)
