"""Tests for the request-scoped structured logging helper (S102)."""

from __future__ import annotations

import pytest
from loop_control_plane.logging import (
    REQUEST_ID_HEADER,
    RequestLogContext,
    configure_for_capture,
    extract_request_id,
)


def test_extract_request_id_passes_through_header() -> None:
    rid = extract_request_id({REQUEST_ID_HEADER: "abc-123"})
    assert rid == "abc-123"


def test_extract_request_id_is_case_insensitive() -> None:
    rid = extract_request_id({"x-request-id": "lower"})
    assert rid == "lower"


def test_extract_request_id_generates_uuid_when_missing() -> None:
    rid = extract_request_id({"unrelated": "value"})
    assert rid and len(rid) == 32  # uuid4().hex


def test_extract_request_id_ignores_blank_value() -> None:
    rid = extract_request_id({REQUEST_ID_HEADER: "   "})
    assert rid and rid != "   "
    assert len(rid) == 32


def test_request_log_context_emits_one_completion_line() -> None:
    logger, cap = configure_for_capture()
    with RequestLogContext(
        method="GET",
        path="/v1/me",
        headers={REQUEST_ID_HEADER: "rid-1"},
        logger=logger,
    ) as ctx:
        ctx.set_status(200)

    completions = [e for e in cap.events if e.get("event") == "request.completed"]
    assert len(completions) == 1
    line = completions[0]
    assert line["method"] == "GET"
    assert line["path"] == "/v1/me"
    assert line["status"] == 200
    assert line["request_id"] == "rid-1"
    assert isinstance(line["latency_ms"], int)
    assert line["latency_ms"] >= 0


def test_request_log_context_records_500_on_unhandled_exception() -> None:
    logger, cap = configure_for_capture()
    with pytest.raises(RuntimeError), RequestLogContext(
        method="POST",
        path="/v1/things",
        headers={},
        logger=logger,
    ):
        raise RuntimeError("boom")

    completions = [e for e in cap.events if e.get("event") == "request.completed"]
    assert len(completions) == 1
    assert completions[0]["status"] == 500


def test_request_log_context_uses_explicit_request_id_over_headers() -> None:
    logger, cap = configure_for_capture()
    with RequestLogContext(
        method="GET",
        path="/",
        headers={REQUEST_ID_HEADER: "from-header"},
        request_id="from-arg",
        logger=logger,
    ) as ctx:
        ctx.set_status(204)
    assert ctx.request_id == "from-arg"
    completion = next(e for e in cap.events if e.get("event") == "request.completed")
    assert completion["request_id"] == "from-arg"


def test_request_log_context_uses_monotonic_clock_for_latency() -> None:
    logger, cap = configure_for_capture()
    ticks = iter([1_000_000_000, 1_000_000_000 + 7_500_000])  # 7.5ms apart

    def fake_clock() -> int:
        return next(ticks)

    with RequestLogContext(
        method="GET",
        path="/",
        headers={REQUEST_ID_HEADER: "x"},
        logger=logger,
        clock=fake_clock,
    ) as ctx:
        ctx.set_status(200)

    completion = next(e for e in cap.events if e.get("event") == "request.completed")
    assert completion["latency_ms"] == 7
