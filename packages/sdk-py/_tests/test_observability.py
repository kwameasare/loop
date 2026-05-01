"""Tests for the loop.observability tracer surface."""

from __future__ import annotations

import json

import pytest
from loop.observability import ClickHouseSpanExporter, reset_for_test, tracer
from loop.observability._tracing import _build_exporter
from opentelemetry.sdk.trace.export import SpanExportResult


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
    with (
        pytest.raises(ValueError, match="Invalid span kind"),
        tracer.span(
            "oops",
            kind="database",  # type: ignore[arg-type]
        ),
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


def test_clickhouse_exporter_writes_json_each_row() -> None:
    exporter = reset_for_test()
    with tracer.span(
        "turn.execute",
        kind="llm",
        attrs={
            "workspace_id": "11111111-1111-1111-1111-111111111111",
            "conversation_id": "22222222-2222-2222-2222-222222222222",
            "turn_id": "33333333-3333-3333-3333-333333333333",
            "cost_usd": 0.125,
        },
    ):
        pass

    sent: list[tuple[str, bytes, float]] = []
    clickhouse = ClickHouseSpanExporter(
        endpoint="http://clickhouse:8123",
        transport=lambda url, body, timeout: sent.append((url, body, timeout)),
    )

    result = clickhouse.export(exporter.get_finished_spans())

    assert result is SpanExportResult.SUCCESS
    assert "INSERT+INTO+otel_traces+FORMAT+JSONEachRow" in sent[0][0]
    row = json.loads(sent[0][1].decode())
    assert row["workspace_id"] == "11111111-1111-1111-1111-111111111111"
    assert row["span_kind"] == "llm"
    assert row["name"] == "turn.execute"
    assert row["cost_usd"] == "0.125"
    assert row["status"] == "ok"


def test_clickhouse_exporter_reports_transport_failure() -> None:
    def boom(url: str, body: bytes, timeout: float) -> None:
        _ = (url, body, timeout)
        raise OSError("clickhouse unavailable")

    clickhouse = ClickHouseSpanExporter(endpoint="http://clickhouse:8123", transport=boom)

    assert clickhouse.export(reset_for_test().get_finished_spans()) is SpanExportResult.SUCCESS
    exporter = reset_for_test()
    with tracer.span("turn.execute", kind="llm"):
        pass
    assert clickhouse.export(exporter.get_finished_spans()) is SpanExportResult.FAILURE


def test_exporter_selection_supports_clickhouse_and_inmemory(monkeypatch) -> None:
    monkeypatch.setenv("LOOP_OTEL_EXPORTER", "clickhouse")
    monkeypatch.setenv("LOOP_OTEL_ENDPOINT", "http://clickhouse:8123")
    assert isinstance(_build_exporter(), ClickHouseSpanExporter)

    monkeypatch.setenv("LOOP_OTEL_EXPORTER", "inmemory")
    assert _build_exporter().__class__.__name__ == "InMemorySpanExporter"
