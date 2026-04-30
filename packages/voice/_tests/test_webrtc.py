"""Tests for the WebRTC signaling layer (S033)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from loop_voice import (
    WebRTCError,
    WebRTCSessionRegistry,
    WebRTCSessionState,
    WebRTCSignal,
    echo_answer_for,
)
from pydantic import ValidationError


def _offer(sdp: str = "v=0\r\no=offer\r\n") -> WebRTCSignal:
    return WebRTCSignal(kind="offer", sdp=sdp)


def test_negotiate_creates_session_and_returns_synthesized_answer() -> None:
    reg = WebRTCSessionRegistry()
    conv = uuid4()
    session, answer = reg.negotiate(
        conversation_id=conv, offer=_offer(), now_ms=1_000
    )
    assert session.state is WebRTCSessionState.CONNECTED
    assert session.sdp_answer is not None
    assert answer.kind == "answer"
    assert answer.sdp == session.sdp_answer
    assert answer.sdp == echo_answer_for("v=0\r\no=offer\r\n")
    assert session.connected_at_ms == 1_000


def test_negotiate_rejects_non_offer_or_empty_offer() -> None:
    reg = WebRTCSessionRegistry()
    conv = uuid4()
    with pytest.raises(WebRTCError):
        reg.negotiate(
            conversation_id=conv,
            offer=WebRTCSignal(kind="answer", sdp="x"),
            now_ms=1,
        )
    with pytest.raises(WebRTCError):
        reg.negotiate(
            conversation_id=conv,
            offer=WebRTCSignal(kind="offer", sdp=None),
            now_ms=1,
        )


def test_add_ice_appends_to_session_and_rejects_after_close() -> None:
    reg = WebRTCSessionRegistry()
    session, _ = reg.negotiate(
        conversation_id=uuid4(), offer=_offer(), now_ms=1
    )
    updated = reg.add_ice(
        session.id, WebRTCSignal(kind="ice", candidate="candidate:1 udp")
    )
    assert updated.ice_candidates == ("candidate:1 udp",)

    reg.close(session.id, now_ms=2)
    with pytest.raises(WebRTCError):
        reg.add_ice(
            session.id,
            WebRTCSignal(kind="ice", candidate="candidate:2 udp"),
        )


def test_add_ice_rejects_non_ice_or_empty_candidate() -> None:
    reg = WebRTCSessionRegistry()
    session, _ = reg.negotiate(
        conversation_id=uuid4(), offer=_offer(), now_ms=1
    )
    with pytest.raises(WebRTCError):
        reg.add_ice(session.id, WebRTCSignal(kind="ice", candidate=None))
    with pytest.raises(WebRTCError):
        reg.add_ice(session.id, WebRTCSignal(kind="answer", sdp="x"))


def test_close_is_idempotent_and_drops_from_active_list() -> None:
    reg = WebRTCSessionRegistry()
    session, _ = reg.negotiate(
        conversation_id=uuid4(), offer=_offer(), now_ms=1
    )
    closed = reg.close(session.id, now_ms=2)
    again = reg.close(session.id, now_ms=3)
    assert closed.state is WebRTCSessionState.CLOSED
    assert again.closed_at_ms == closed.closed_at_ms  # idempotent
    assert reg.list_active() == []


def test_get_unknown_session_raises() -> None:
    reg = WebRTCSessionRegistry()
    with pytest.raises(WebRTCError):
        reg.get(uuid4())


def test_signal_is_frozen_strict() -> None:
    s = WebRTCSignal(kind="ice", candidate="x")
    with pytest.raises(ValidationError):
        WebRTCSignal(kind="ice", candidate="x", sdp_mline_index=-1)
    # frozen
    with pytest.raises(ValidationError):
        s.model_validate(s.model_dump() | {"kind": "bogus"})
