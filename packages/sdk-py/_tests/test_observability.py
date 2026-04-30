"""Tests for the loop.observability tracer surface."""

from __future__ import annotations

import pytest
from loop.observability import reset_for_test, tracer


def test_span_emits_with_required_attrs() -> None:
    exporter = reset_for_test()
    with tracer.span(
        "turn.execute",
        kind="llm",
        attrs={
            "workspace_id": "w-1",
            "conversation_id": "c-1",
            "turn_id": "t-1",
            "agent_id": "support",
        },
    ) as span:
        span.set_attr("model", "gpt-4o-mini")
        span.set_attr("input_tokens", 10)

    finished = exporter.get_finished_spans()
    assert len(finished) == 1
    s = finished[0]
    assert s.name == "turn.execute"
    attrs = dict(s.attributes or {})
    assert attrs["loop.span.kind"] == "llm"
    assert attrs["workspace_id"] == "w-1"
    assert attrs["agent_id"] == "support"
    assert attrs["model"] == "gpt-4o-mini"
    assert attrs["input_tokens"] == 10


def test_invalid_span_kind_rejected() -> None:
    reset_for_test()
    with pytest.raises(ValueError, match="Invalid span kind"), tracer.span(
        "oops",
        kind="database",  # type: ignore[arg-type]
    ):
        pass


def test_exception_records_loop_error_code() -> None:
    exporter = reset_for_test()

    class _BoomError(RuntimeError):
        code = "GW-PARSE"

    with pytest.raises(_BoomError), tracer.span("turn.execute", kind="llm") as span:
        span.set_attr("workspace_id", "w-1")
        raise _BoomError("upstream parse failure")

    finished = exporter.get_finished_spans()
    assert len(finished) == 1
    attrs = dict(finished[0].attributes or {})
    assert attrs["loop.error.code"] == "GW-PARSE"
    assert finished[0].status.status_code.name == "ERROR"


async def test_aspan_works_in_async_context() -> None:
    exporter = reset_for_test()
    async with tracer.aspan(
        "memory.load",
        kind="memory",
        attrs={"workspace_id": "w-2"},
    ) as span:
        span.set_attr("memory.session_keys", 3)

    finished = exporter.get_finished_spans()
    assert len(finished) == 1
    assert finished[0].name == "memory.load"
    attrs = dict(finished[0].attributes or {})
    assert attrs["loop.span.kind"] == "memory"
    assert attrs["memory.session_keys"] == 3
