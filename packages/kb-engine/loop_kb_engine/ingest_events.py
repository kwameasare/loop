"""Ingest progress pub/sub (S210).

A small async fan-out so the cp-api can subscribe to ingest progress
without coupling kb-engine to a concrete broker. Production wires this
to NATS or Redis pub/sub via a ``ProgressSink`` adapter.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "IngestEvent",
    "IngestEventBus",
    "ProgressSink",
]


IngestEventKind = Literal[
    "document.received",
    "document.chunked",
    "document.embedded",
    "document.indexed",
    "document.failed",
]


class IngestEvent(BaseModel):
    """Progress event emitted during document ingestion."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    workspace_id: UUID
    document_id: UUID
    kind: IngestEventKind
    chunks_total: int | None = Field(default=None, ge=0)
    chunks_done: int | None = Field(default=None, ge=0)
    error: str | None = Field(default=None, max_length=512)


@runtime_checkable
class ProgressSink(Protocol):
    """Adapter for forwarding events outside the process."""

    async def emit(self, event: IngestEvent) -> None: ...


@dataclass
class IngestEventBus:
    """In-memory async fan-out with optional external sink."""

    sink: ProgressSink | None = None
    _subscribers: list[asyncio.Queue[IngestEvent]] = field(default_factory=list)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def publish(self, event: IngestEvent) -> None:
        async with self._lock:
            queues = list(self._subscribers)
        for q in queues:
            await q.put(event)
        if self.sink is not None:
            await self.sink.emit(event)

    async def subscribe(
        self,
        *,
        maxsize: int = 256,
    ) -> AsyncIterator[IngestEvent]:
        """Async iterator yielding events. Caller awaits a ``__anext__`` loop."""

        q: asyncio.Queue[IngestEvent] = asyncio.Queue(maxsize=maxsize)
        async with self._lock:
            self._subscribers.append(q)
        try:
            while True:
                yield await q.get()
        finally:
            async with self._lock:
                if q in self._subscribers:
                    self._subscribers.remove(q)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)
