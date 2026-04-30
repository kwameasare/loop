"""Smoke tests for the public SDK types (S004).

These pin down the wire shapes the runtime, channels, and SDK consumers
all depend on. Any failure here is a *breaking* SDK change — see AGENTS.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from loop import (
    AgentEvent,
    AgentResponse,
    ChannelType,
    ContentPart,
    Span,
    ToolCall,
    Trace,
    Turn,
    TurnEvent,
    TurnStatus,
)
from pydantic import ValidationError


def _ws() -> UUID:
    return uuid4()


def _conv() -> UUID:
    return uuid4()


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _evt() -> AgentEvent:
    return AgentEvent(
        workspace_id=_ws(),
        conversation_id=_conv(),
        user_id="u-1",
        channel=ChannelType.WEB,
        content=[ContentPart(type="text", text="hello")],
        received_at=_now(),
    )


# --------------------------------------------------------------------------- #
# Construction                                                                #
# --------------------------------------------------------------------------- #


def test_agent_event_round_trip() -> None:
    evt = _evt()
    raw = evt.model_dump_json()
    reborn = AgentEvent.model_validate_json(raw)
    assert reborn == evt
    assert reborn.channel is ChannelType.WEB


def test_agent_response_defaults() -> None:
    resp = AgentResponse(conversation_id=_conv(), content=[ContentPart(type="text", text="ok")])
    assert resp.streaming is True
    assert resp.end_turn is True
    assert resp.suggested_actions == []


def test_turn_event_payload_is_freeform() -> None:
    ev = TurnEvent(type="token", payload={"text": "hi"}, ts=_now())
    assert ev.type == "token"


def test_tool_call_defaults() -> None:
    tc = ToolCall(name="search", server="loop-hub://web@1", args={"q": "foo"})
    assert tc.cost_usd == 0.0
    assert tc.latency_ms == 0
    assert tc.error is None


def test_trace_aggregates_spans() -> None:
    span = Span(
        span_id=uuid4(),
        kind="llm",
        name="gateway.stream",
        started_at=_now(),
    )
    trace = Trace(turn_id=uuid4(), spans=[span], total_cost_usd=0.012, iteration_count=1)
    assert len(trace.spans) == 1
    assert trace.iteration_count == 1


def test_turn_aggregate() -> None:
    evt = _evt()
    t = Turn(
        workspace_id=evt.workspace_id,
        conversation_id=evt.conversation_id,
        agent_name="support",
        event=evt,
        started_at=_now(),
    )
    assert t.status is TurnStatus.PENDING
    assert isinstance(t.turn_id, UUID)
    assert t.cost_usd == 0.0


# --------------------------------------------------------------------------- #
# Boundary safety                                                             #
# --------------------------------------------------------------------------- #


def test_extra_fields_rejected() -> None:
    """Public types are strict — typos at the wire boundary must fail loud."""
    with pytest.raises(ValidationError):
        AgentEvent.model_validate(
            {
                "workspace_id": str(_ws()),
                "conversation_id": str(_conv()),
                "user_id": "u-1",
                "channel": "web",
                "content": [{"type": "text", "text": "hi"}],
                "received_at": _now().isoformat(),
                "totally_not_a_field": 1,
            }
        )


def test_turn_event_type_literal_enforced() -> None:
    with pytest.raises(ValidationError):
        TurnEvent(type="bogus", payload={}, ts=_now())  # type: ignore[arg-type]


def test_channel_type_round_trip_via_string() -> None:
    evt = AgentEvent.model_validate(
        {
            "workspace_id": str(_ws()),
            "conversation_id": str(_conv()),
            "user_id": "u-1",
            "channel": "whatsapp",
            "content": [],
            "received_at": _now().isoformat(),
        }
    )
    assert evt.channel is ChannelType.WHATSAPP
