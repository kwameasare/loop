"""Production-replay capture for failed turns (S026).

The runtime emits a ``FailedTurn`` record whenever a production turn ends in a
``degrade`` event, an unrecovered tool error, or a final completion that the
caller flags as a regression candidate (e.g. user thumbs-down). This module
captures, samples, optionally redacts, and converts those records into
``loop_eval.Sample`` rows so the eval harness can replay them.

Public surface:

* ``FailedTurn`` -- pydantic v2 model (frozen, strict) describing one captured
  failure.
* ``ReplaySink`` Protocol + ``InMemoryReplaySink`` test double.
* ``should_capture`` -- deterministic, hash-based sampling decision keyed on
  ``(workspace_id, request_id)`` so retries of the same turn make the same
  decision.
* ``capture`` -- high-level helper that applies sampling and an optional
  redactor before pushing into the sink.
* ``to_samples`` -- project a list of captured turns into eval ``Sample`` rows.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from loop_eval.models import Sample


class FailedTurn(BaseModel):
    """One captured production failure."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    workspace_id: UUID
    agent_id: UUID
    request_id: str = Field(min_length=1)
    input_text: str
    output_text: str = ""
    failure_reason: str = Field(min_length=1)
    timestamp_ms: int = Field(ge=0)
    metadata: dict[str, str] = Field(default_factory=dict)


class ReplaySink(Protocol):
    """Where captured failed turns go."""

    async def append(self, turn: FailedTurn) -> None: ...

    async def list(self) -> list[FailedTurn]: ...


@dataclass
class InMemoryReplaySink:
    """In-process sink suitable for tests + dev compose."""

    items: list[FailedTurn] = field(default_factory=list)

    async def append(self, turn: FailedTurn) -> None:
        self.items.append(turn)

    async def list(self) -> list[FailedTurn]:
        return list(self.items)


def should_capture(
    *,
    workspace_id: UUID,
    request_id: str,
    sample_rate: float,
) -> bool:
    """Deterministic sampling on ``(workspace_id, request_id)``.

    Returns ``True`` for ``sample_rate * total`` of the keyspace. The decision
    is stable across retries -- the same key always produces the same answer.
    """

    if sample_rate <= 0.0:
        return False
    if sample_rate >= 1.0:
        return True
    digest = hashlib.sha256(f"{workspace_id}:{request_id}".encode()).digest()
    bucket = int.from_bytes(digest[:4], "big") / 0xFFFFFFFF
    return bucket < sample_rate


Redactor = Callable[[str], str]


async def capture(
    *,
    sink: ReplaySink,
    turn: FailedTurn,
    sample_rate: float,
    redactor: Redactor | None = None,
) -> bool:
    """Apply sampling + redaction and push to sink.

    Returns ``True`` if the turn was actually appended.
    """

    if not should_capture(
        workspace_id=turn.workspace_id,
        request_id=turn.request_id,
        sample_rate=sample_rate,
    ):
        return False
    final = turn
    if redactor is not None:
        final = turn.model_copy(
            update={
                "input_text": redactor(turn.input_text),
                "output_text": redactor(turn.output_text),
            }
        )
    await sink.append(final)
    return True


def to_samples(turns: list[FailedTurn]) -> list[Sample]:
    """Project captured failures into eval samples.

    Sample id is derived from ``request_id`` so re-captures don't double-count.
    """

    return [
        Sample(
            id=f"replay-{t.request_id}",
            input=t.input_text,
            expected=t.output_text or None,
            metadata={
                "failure_reason": t.failure_reason,
                "workspace_id": str(t.workspace_id),
                "agent_id": str(t.agent_id),
                "timestamp_ms": str(t.timestamp_ms),
                **t.metadata,
            },
        )
        for t in turns
    ]


__all__ = [
    "FailedTurn",
    "InMemoryReplaySink",
    "ReplaySink",
    "capture",
    "should_capture",
    "to_samples",
]
