"""Tests for from_turn_event mapping + SSE wire shape for tool calls."""

from __future__ import annotations

import json
from uuid import uuid4

from loop_channels_core import (
    OutboundFrameKind,
    from_turn_event,
)


def test_token_event_maps_to_agent_token() -> None:
    convo = uuid4()
    frame = from_turn_event(
        event_type="token",
        payload={"text": "hello"},
        conversation_id=convo,
        sequence=0,
    )
    assert frame is not None
    assert frame.kind is OutboundFrameKind.AGENT_TOKEN
    assert frame.text == "hello"


def test_tool_call_start_serialises_arguments_as_json() -> None:
    frame = from_turn_event(
        event_type="tool_call_start",
        payload={"id": "c1", "name": "search", "arguments": {"q": "x", "k": 5}},
        conversation_id=uuid4(),
        sequence=2,
    )
    assert frame is not None
    assert frame.kind is OutboundFrameKind.TOOL_CALL_START
    args = json.loads(frame.payload["arguments"])
    assert args == {"q": "x", "k": 5}
    assert frame.payload["id"] == "c1"
    assert frame.payload["name"] == "search"


def test_tool_call_end_carries_latency_and_error() -> None:
    frame = from_turn_event(
        event_type="tool_call_end",
        payload={
            "id": "c1",
            "name": "search",
            "result": "ok",
            "error": None,
            "latency_ms": 42,
        },
        conversation_id=uuid4(),
        sequence=3,
    )
    assert frame is not None
    assert frame.kind is OutboundFrameKind.TOOL_CALL_END
    assert frame.payload["result"] == "ok"
    assert frame.payload["error"] == ""
    assert frame.payload["latency_ms"] == "42"


def test_complete_event_extracts_first_text_part() -> None:
    frame = from_turn_event(
        event_type="complete",
        payload={"content": [{"type": "text", "text": "all done"}]},
        conversation_id=uuid4(),
        sequence=10,
    )
    assert frame is not None
    assert frame.kind is OutboundFrameKind.AGENT_MESSAGE
    assert frame.text == "all done"


def test_degrade_event_maps_to_error_with_code() -> None:
    frame = from_turn_event(
        event_type="degrade",
        payload={"reason": "max_iterations", "message": "looped"},
        conversation_id=uuid4(),
        sequence=4,
    )
    assert frame is not None
    assert frame.kind is OutboundFrameKind.ERROR
    assert frame.payload["code"] == "max_iterations"
    assert frame.text == "looped"


def test_unknown_event_is_dropped() -> None:
    out = from_turn_event(
        event_type="trace",
        payload={"span_id": "x"},
        conversation_id=uuid4(),
        sequence=0,
    )
    assert out is None
