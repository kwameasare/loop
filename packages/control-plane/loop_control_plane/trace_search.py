"""Trace search API (S287) — query persisted spans by turn_id, conv_id,
or time-range from the cp-api UI.

The studio "Traces" page (S288/S289) renders a list and waterfall.
The list-side query is exposed here as a pure service that talks to
a :class:`TraceStore` Protocol — the production binding is a thin
ClickHouse wrapper, the test binding is :class:`InMemoryTraceStore`.

A query carries the workspace_id (always required for tenant
isolation), one or more optional filters, and pagination.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = [
    "InMemoryTraceStore",
    "TraceQuery",
    "TraceQueryResult",
    "TraceSearchService",
    "TraceStore",
    "TraceSummary",
]


_MAX_PAGE_SIZE: int = 200


class TraceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    workspace_id: UUID
    trace_id: str = Field(min_length=32, max_length=32)
    turn_id: UUID
    conversation_id: UUID
    agent_id: UUID
    started_at: datetime
    duration_ms: int = Field(ge=0)
    span_count: int = Field(ge=1)
    error: bool = False


class TraceQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    workspace_id: UUID
    turn_id: UUID | None = None
    conversation_id: UUID | None = None
    agent_id: UUID | None = None
    started_at_from: datetime | None = None
    started_at_to: datetime | None = None
    only_errors: bool = False
    page_size: int = Field(default=50, ge=1, le=_MAX_PAGE_SIZE)
    cursor: str | None = None  # opaque "started_at|trace_id" pair

    @model_validator(mode="after")
    def _validate_window(self) -> TraceQuery:
        if (
            self.started_at_from is not None
            and self.started_at_to is not None
            and self.started_at_from > self.started_at_to
        ):
            raise ValueError("started_at_from must be <= started_at_to")
        return self


class TraceQueryResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    items: tuple[TraceSummary, ...]
    next_cursor: str | None = None


class TraceStore(Protocol):
    async def search(self, query: TraceQuery) -> Sequence[TraceSummary]: ...


class InMemoryTraceStore:
    """Test binding. Keeps an in-memory list and applies the same
    semantics the ClickHouse binding will: workspace-scoped, ordered
    by ``started_at DESC, trace_id DESC``, opaque cursor pagination.
    """

    def __init__(self, traces: Sequence[TraceSummary] | None = None) -> None:
        self._traces: list[TraceSummary] = list(traces or ())

    def add(self, trace: TraceSummary) -> None:
        self._traces.append(trace)

    async def search(self, query: TraceQuery) -> Sequence[TraceSummary]:
        rows = [t for t in self._traces if t.workspace_id == query.workspace_id]
        if query.turn_id is not None:
            rows = [t for t in rows if t.turn_id == query.turn_id]
        if query.conversation_id is not None:
            rows = [t for t in rows if t.conversation_id == query.conversation_id]
        if query.agent_id is not None:
            rows = [t for t in rows if t.agent_id == query.agent_id]
        if query.started_at_from is not None:
            rows = [t for t in rows if t.started_at >= query.started_at_from]
        if query.started_at_to is not None:
            rows = [t for t in rows if t.started_at <= query.started_at_to]
        if query.only_errors:
            rows = [t for t in rows if t.error]
        # Sort newest-first, deterministic tiebreak on trace_id.
        rows.sort(key=lambda t: (t.started_at, t.trace_id), reverse=True)
        if query.cursor is not None:
            cursor = _parse_cursor(query.cursor)
            rows = [
                t for t in rows if (t.started_at, t.trace_id) < cursor
            ]
        # Page.
        return rows[: query.page_size + 1]  # +1 sentinel for next_cursor


class TraceSearchService:
    """Public façade — the FastAPI handler calls ``run``."""

    def __init__(self, store: TraceStore) -> None:
        self._store = store

    async def run(self, query: TraceQuery) -> TraceQueryResult:
        rows = list(await self._store.search(query))
        if len(rows) > query.page_size:
            page = rows[: query.page_size]
            tail = page[-1]
            cursor = _format_cursor(tail.started_at, tail.trace_id)
            return TraceQueryResult(items=tuple(page), next_cursor=cursor)
        return TraceQueryResult(items=tuple(rows), next_cursor=None)


def _format_cursor(started_at: datetime, trace_id: str) -> str:
    return f"{started_at.isoformat()}|{trace_id}"


def _parse_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        ts_str, trace_id = cursor.split("|", 1)
    except ValueError as exc:
        raise ValueError(f"malformed cursor: {cursor!r}") from exc
    return datetime.fromisoformat(ts_str), trace_id
