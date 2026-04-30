"""Server-Sent-Events (SSE) wire encoder for the dp-runtime ``/v1/turns``
streaming endpoint (S135).

The cp-api / sdk-py / studio web-channel-js all consume the same SSE
format. Keeping the encoder here means there is exactly one place
that knows the byte-shape of a Loop streaming turn — every consumer
either reuses :class:`SseEncoder` directly (Python) or generates an
identical decoder from the documented frame grammar (TypeScript).

Wire grammar (one frame per ``encode``)::

    event: <kind>\\n
    id: <monotonic-int>\\n
    data: <json>\\n
    \\n

The trailing blank line is the SSE record terminator. ``id:`` is a
strictly-monotonic integer per stream so a reconnecting client can
send ``Last-Event-Id`` and the server can resume from the next id.
JSON is encoded with ``separators=(",", ":")`` so the wire is
deterministic and easy to compare in tests.

The encoder is *pure* — no I/O, no async — so unit tests can assert
exact byte sequences.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from enum import StrEnum
from typing import Any

__all__ = [
    "SseEncoder",
    "SseEventKind",
    "SseFrame",
    "SseFrameError",
    "encode_done",
    "encode_error",
    "encode_keepalive",
    "encode_turn_event",
]


class SseEventKind(StrEnum):
    """Canonical event names that go on the ``event:`` line."""

    TURN_EVENT = "turn_event"
    DONE = "done"
    ERROR = "error"
    KEEPALIVE = "keepalive"


class SseFrameError(ValueError):
    """Raised when an attempted frame would violate the wire contract.

    Surfaced to the caller (the FastAPI handler) which converts it
    into a 500 with code ``LOOP-RT-SSE-001`` rather than emitting a
    malformed frame the client cannot recover from.
    """


class SseFrame:
    """Single, immutable, framed SSE record.

    Attributes are validated on construction so a malformed frame is
    caught at the producer rather than corrupting the stream.
    """

    __slots__ = ("_data", "_event_id", "_kind")

    def __init__(self, *, kind: SseEventKind, event_id: int, data: str) -> None:
        if event_id < 0:
            raise SseFrameError(f"event_id must be >= 0, got {event_id}")
        if "\n" in data:
            raise SseFrameError("data must already be a single-line JSON string")
        self._kind = kind
        self._event_id = event_id
        self._data = data

    @property
    def kind(self) -> SseEventKind:
        return self._kind

    @property
    def event_id(self) -> int:
        return self._event_id

    @property
    def data(self) -> str:
        return self._data

    def to_bytes(self) -> bytes:
        # Always exactly four lines: event, id, data, blank.
        # Wire is ASCII-safe because JSON escapes non-ASCII into \uXXXX.
        line = (
            f"event: {self._kind.value}\n"
            f"id: {self._event_id}\n"
            f"data: {self._data}\n"
            "\n"
        )
        return line.encode("utf-8")


class SseEncoder:
    """Stateful encoder that mints monotonic ``event_id`` values.

    Re-using a single encoder across one HTTP response guarantees ids
    stay monotonic. Concurrent streams MUST use separate encoders.
    """

    def __init__(self, *, start_id: int = 0) -> None:
        if start_id < 0:
            raise SseFrameError(f"start_id must be >= 0, got {start_id}")
        self._next_id = start_id

    @property
    def next_id(self) -> int:
        return self._next_id

    def encode(self, kind: SseEventKind, payload: object) -> bytes:
        data = _to_compact_json(payload)
        frame = SseFrame(kind=kind, event_id=self._next_id, data=data)
        self._next_id += 1
        return frame.to_bytes()

    def encode_many(self, items: Iterable[tuple[SseEventKind, object]]) -> bytes:
        out: list[bytes] = []
        for kind, payload in items:
            out.append(self.encode(kind, payload))
        return b"".join(out)


def _to_compact_json(payload: object) -> str:
    if isinstance(payload, str):
        # Raw string payloads are JSON-encoded so the data line stays
        # single-line and quoted, which the SDK decoders can rely on.
        return json.dumps(payload, separators=(",", ":"))
    return json.dumps(payload, separators=(",", ":"), default=_default)


def _default(obj: Any) -> Any:
    # Pydantic v2 BaseModel + StrEnum + UUID + datetime are the four
    # types the runtime hands us; they all expose either model_dump,
    # str(), or isoformat. Anything else is a producer bug.
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


def encode_turn_event(encoder: SseEncoder, payload: object) -> bytes:
    return encoder.encode(SseEventKind.TURN_EVENT, payload)


def encode_done(encoder: SseEncoder, *, turn_id: str) -> bytes:
    return encoder.encode(SseEventKind.DONE, {"turn_id": turn_id})


def encode_error(encoder: SseEncoder, *, code: str, message: str) -> bytes:
    return encoder.encode(SseEventKind.ERROR, {"code": code, "message": message})


def encode_keepalive(encoder: SseEncoder) -> bytes:
    return encoder.encode(SseEventKind.KEEPALIVE, {"ts_ms": 0})
