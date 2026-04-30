"""Turn persistence service (S137).

When ``TurnExecutor`` emits a ``complete`` :class:`TurnEvent`, the
runtime must atomically write:

  * one row into ``turns`` capturing the final state;
  * N rows into ``tool_calls`` for each tool invocation.

This module defines the service shape. Tests run against the
:class:`InMemoryTurnSink`. The Postgres adapter (production) wraps a
SQL transaction so the two writes commit together — no orphan
turn rows, no orphan tool_call rows.

The shape is idempotent on ``turn_id``: re-applying the same record
is a no-op. The runtime's at-least-once delivery from the SSE close
handler can therefore retry after a transient DB failure.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "InMemoryTurnSink",
    "PersistedToolCall",
    "PersistedTurn",
    "TurnPersistence",
    "TurnPersistenceError",
    "TurnSink",
]


class TurnPersistenceError(RuntimeError):
    """Raised on a non-idempotent re-apply or a transport failure."""


class PersistedToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: UUID
    turn_id: UUID
    tool_name: str = Field(min_length=1, max_length=128)
    arguments_json: str
    result_json: str | None
    error: str | None = None
    started_at: datetime
    finished_at: datetime | None


class PersistedTurn(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: UUID
    workspace_id: UUID
    conversation_id: UUID
    agent_version_id: UUID
    started_at: datetime
    finished_at: datetime
    output_text: str
    cost_usd: float = Field(ge=0.0)
    tokens_in: int = Field(ge=0)
    tokens_out: int = Field(ge=0)


class TurnSink(Protocol):
    async def insert_turn(
        self,
        *,
        turn: PersistedTurn,
        tool_calls: Sequence[PersistedToolCall],
    ) -> bool:
        """Returns True iff the row was newly inserted (idempotent re-apply → False)."""

    async def get(self, turn_id: UUID) -> PersistedTurn | None: ...

    async def list_tool_calls(self, turn_id: UUID) -> tuple[PersistedToolCall, ...]: ...


class InMemoryTurnSink:
    def __init__(self) -> None:
        self._turns: dict[UUID, PersistedTurn] = {}
        self._tool_calls: dict[UUID, list[PersistedToolCall]] = {}
        self._lock = asyncio.Lock()

    async def insert_turn(
        self,
        *,
        turn: PersistedTurn,
        tool_calls: Sequence[PersistedToolCall],
    ) -> bool:
        async with self._lock:
            if turn.id in self._turns:
                # Cross-check idempotency: the resubmitted row must
                # match the stored one bit-for-bit. A divergent retry
                # is a bug and we must not silently overwrite.
                if self._turns[turn.id] != turn:
                    raise TurnPersistenceError(
                        f"divergent re-apply of turn {turn.id}"
                    )
                return False
            for tc in tool_calls:
                if tc.turn_id != turn.id:
                    raise TurnPersistenceError(
                        f"tool_call {tc.id} has turn_id {tc.turn_id}, expected {turn.id}"
                    )
            self._turns[turn.id] = turn
            self._tool_calls[turn.id] = list(tool_calls)
            return True

    async def get(self, turn_id: UUID) -> PersistedTurn | None:
        async with self._lock:
            return self._turns.get(turn_id)

    async def list_tool_calls(self, turn_id: UUID) -> tuple[PersistedToolCall, ...]:
        async with self._lock:
            return tuple(self._tool_calls.get(turn_id, ()))


class TurnPersistence:
    """Thin façade over a :class:`TurnSink` with telemetry hooks.

    The runtime calls :meth:`persist_complete` when the SSE
    ``complete`` frame closes. Persisting is structured separately
    from emitting so the streaming path is never blocked by the DB.
    """

    def __init__(self, sink: TurnSink) -> None:
        self._sink = sink

    async def persist_complete(
        self,
        *,
        turn: PersistedTurn,
        tool_calls: Sequence[PersistedToolCall],
    ) -> bool:
        return await self._sink.insert_turn(turn=turn, tool_calls=tool_calls)

    async def lookup(self, turn_id: UUID) -> tuple[PersistedTurn | None, tuple[PersistedToolCall, ...]]:
        turn = await self._sink.get(turn_id)
        calls = await self._sink.list_tool_calls(turn_id) if turn else ()
        return turn, calls

    @staticmethod
    def select_count_query(workspace_id: UUID, conversation_id: UUID) -> tuple[str, dict[str, Any]]:
        """The exact integration-test assertion: ``SELECT count(*) FROM turns WHERE conversation_id=$1``.

        Returned as a parametrised query so the integration suite
        can run it through SQLAlchemy without string-interpolating
        UUIDs.
        """
        return (
            "SELECT COUNT(*) FROM turns WHERE workspace_id = :ws AND conversation_id = :conv",
            {"ws": str(workspace_id), "conv": str(conversation_id)},
        )
