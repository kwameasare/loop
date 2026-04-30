"""Inbox event bus (S304).

Mirrors ``loop_kb_engine.ingest_events`` shape so the studio + audit
pipelines have a uniform pub/sub surface across product domains. Each
takeover_started/ended (and escalate/release/resolve) state change
publishes a typed event that downstream subscribers — studio live
inbox view, audit log, NATS bridge — consume via ``subscribe()``.

This module deliberately knows nothing about NATS: production wires a
``ProgressSink`` adapter that publishes to ``loop.inbox.*`` subjects.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

InboxEventKind = Literal[
    "inbox.escalated",
    "inbox.takeover_started",
    "inbox.takeover_ended",
    "inbox.resolved",
]


class InboxEvent(BaseModel):
    """Published whenever an inbox item changes state."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    workspace_id: UUID
    item_id: UUID
    conversation_id: UUID
    kind: InboxEventKind
    operator_id: str | None = None
    timestamp_ms: int = Field(ge=0)
    note: str = Field(default="", max_length=500)


@runtime_checkable
class ProgressSink(Protocol):
    async def publish(self, event: InboxEvent) -> None: ...


@dataclass
class InboxEventBus:
    """In-process async fan-out + optional external sink."""

    sink: ProgressSink | None = None
    _subscribers: list[asyncio.Queue[InboxEvent]] = field(default_factory=list)

    async def publish(self, event: InboxEvent) -> None:
        for queue in list(self._subscribers):
            await queue.put(event)
        if self.sink is not None:
            await self.sink.publish(event)

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[AsyncIterator[InboxEvent]]:
        queue: asyncio.Queue[InboxEvent] = asyncio.Queue()
        self._subscribers.append(queue)
        try:

            async def _iter() -> AsyncIterator[InboxEvent]:
                while True:
                    yield await queue.get()

            yield _iter()
        finally:
            self._subscribers.remove(queue)


__all__ = [
    "InboxEvent",
    "InboxEventBus",
    "InboxEventKind",
    "ProgressSink",
]
