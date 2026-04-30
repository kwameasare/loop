"""WebRTC-shaped signaling for the voice channel.

This module ships the *protocol envelope* (offer / answer / ICE
candidate frames) and a session state machine that the real WebRTC
peer connection (aiortc, in S033b) will plug into.

The signaling layer is transport-agnostic: callers exchange
:class:`WebRTCSignal` objects over whatever they like (REST POST,
WebSocket, etc.). The :class:`WebRTCSessionRegistry` owns the
state of every active session and serialises transitions so a
late ICE candidate or duplicate answer cannot corrupt state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class WebRTCError(RuntimeError):
    """Raised on any signaling state-machine violation."""


class WebRTCSessionState(StrEnum):
    NEGOTIATING = "negotiating"
    CONNECTED = "connected"
    CLOSED = "closed"


SignalKind = Literal["offer", "answer", "ice"]


class WebRTCSignal(BaseModel):
    """One signaling envelope.

    * ``kind == "offer"`` -- ``sdp`` is required, candidate fields unused.
    * ``kind == "answer"`` -- ``sdp`` is required.
    * ``kind == "ice"`` -- ``candidate`` is required.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    kind: SignalKind
    sdp: str | None = None
    candidate: str | None = None
    sdp_mid: str | None = None
    sdp_mline_index: int | None = Field(default=None, ge=0)


class WebRTCSession(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    id: UUID
    conversation_id: UUID
    state: WebRTCSessionState
    sdp_offer: str | None = None
    sdp_answer: str | None = None
    ice_candidates: tuple[str, ...] = ()
    created_at_ms: int = Field(ge=0)
    connected_at_ms: int | None = None
    closed_at_ms: int | None = None

    def with_answer(self, sdp_answer: str, *, now_ms: int) -> WebRTCSession:
        return self.model_copy(
            update={
                "sdp_answer": sdp_answer,
                "state": WebRTCSessionState.CONNECTED,
                "connected_at_ms": now_ms,
            }
        )

    def with_ice(self, candidate: str) -> WebRTCSession:
        return self.model_copy(
            update={"ice_candidates": (*self.ice_candidates, candidate)}
        )

    def with_close(self, *, now_ms: int) -> WebRTCSession:
        return self.model_copy(
            update={"state": WebRTCSessionState.CLOSED, "closed_at_ms": now_ms}
        )


def _validate_offer(signal: WebRTCSignal) -> str:
    if signal.kind != "offer":
        raise WebRTCError(f"expected offer, got {signal.kind!r}")
    if not signal.sdp:
        raise WebRTCError("offer requires a non-empty sdp")
    return signal.sdp


def _validate_ice(signal: WebRTCSignal) -> str:
    if signal.kind != "ice":
        raise WebRTCError(f"expected ice, got {signal.kind!r}")
    if not signal.candidate:
        raise WebRTCError("ice requires a non-empty candidate")
    return signal.candidate


def echo_answer_for(offer_sdp: str) -> str:
    """Build a deterministic SDP answer for the echo MVP.

    Real adapter (S033b) will run this through aiortc's peer
    connection. For v0 we return a synthesised answer so signaling
    can be exercised end-to-end without a media stack.
    """

    return f"v=0\r\no=- echo IN IP4 0.0.0.0\r\na=echo-of:{offer_sdp[:32]}"


@dataclass
class WebRTCSessionRegistry:
    """In-memory registry of WebRTC sessions.

    Not thread-safe -- the surrounding HTTP service is expected to
    serialise per-session signaling.
    """

    _sessions: dict[UUID, WebRTCSession] = field(default_factory=dict)

    def negotiate(
        self,
        *,
        conversation_id: UUID,
        offer: WebRTCSignal,
        now_ms: int,
    ) -> tuple[WebRTCSession, WebRTCSignal]:
        """Accept an SDP offer and produce an SDP answer.

        Creates a fresh session in NEGOTIATING, then transitions it
        to CONNECTED with the synthesized answer. Returns the
        ``(session, answer)`` pair so callers can ship the answer
        back over their signaling transport.
        """

        offer_sdp = _validate_offer(offer)
        sid = uuid4()
        session = WebRTCSession(
            id=sid,
            conversation_id=conversation_id,
            state=WebRTCSessionState.NEGOTIATING,
            sdp_offer=offer_sdp,
            created_at_ms=now_ms,
        )
        answer_sdp = echo_answer_for(offer_sdp)
        session = session.with_answer(answer_sdp, now_ms=now_ms)
        self._sessions[sid] = session
        return session, WebRTCSignal(kind="answer", sdp=answer_sdp)

    def add_ice(self, session_id: UUID, signal: WebRTCSignal) -> WebRTCSession:
        candidate = _validate_ice(signal)
        session = self._require(session_id)
        if session.state == WebRTCSessionState.CLOSED:
            raise WebRTCError(f"session {session_id} is closed")
        updated = session.with_ice(candidate)
        self._sessions[session_id] = updated
        return updated

    def close(self, session_id: UUID, *, now_ms: int) -> WebRTCSession:
        session = self._require(session_id)
        if session.state == WebRTCSessionState.CLOSED:
            return session
        closed = session.with_close(now_ms=now_ms)
        self._sessions[session_id] = closed
        return closed

    def get(self, session_id: UUID) -> WebRTCSession:
        return self._require(session_id)

    def list_active(self) -> list[WebRTCSession]:
        return [
            s
            for s in self._sessions.values()
            if s.state != WebRTCSessionState.CLOSED
        ]

    def _require(self, session_id: UUID) -> WebRTCSession:
        s = self._sessions.get(session_id)
        if s is None:
            raise WebRTCError(f"unknown session {session_id}")
        return s


__all__ = [
    "SignalKind",
    "WebRTCError",
    "WebRTCSession",
    "WebRTCSessionRegistry",
    "WebRTCSessionState",
    "WebRTCSignal",
    "echo_answer_for",
]
