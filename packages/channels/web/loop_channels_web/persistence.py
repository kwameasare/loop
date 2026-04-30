"""Web-channel conversation persistence (S173).

Models ``conversations`` rows whose ``channel_type='web'``. The store
is a Protocol with an in-memory implementation; the production
PostgreSQL adapter swaps in via the same surface.

The store is intentionally narrow — *only* the operations the web
channel needs (create, fetch by token, append-message, end). Broader
conversation CRUD lives in the data-plane.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, replace
from typing import Literal, Protocol, runtime_checkable
from uuid import UUID, uuid4

__all__ = [
    "InMemoryWebConversationStore",
    "WebConversation",
    "WebConversationNotFoundError",
    "WebConversationStore",
    "WebMessage",
    "WebMessageRole",
]


WebMessageRole = Literal["user", "assistant", "system"]


@dataclass(frozen=True)
class WebMessage:
    role: WebMessageRole
    text: str
    created_at_ms: int


@dataclass(frozen=True)
class WebConversation:
    id: UUID
    workspace_id: UUID
    agent_id: UUID
    visitor_id: str
    started_at_ms: int
    ended_at_ms: int | None
    messages: tuple[WebMessage, ...] = field(default_factory=tuple)
    channel_type: Literal["web"] = "web"


class WebConversationNotFoundError(LookupError):
    """No conversation with the given id."""


@runtime_checkable
class WebConversationStore(Protocol):
    async def create(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        visitor_id: str,
        now_ms: int,
    ) -> WebConversation: ...

    async def get(self, conversation_id: UUID) -> WebConversation: ...

    async def append_message(
        self,
        conversation_id: UUID,
        message: WebMessage,
    ) -> WebConversation: ...

    async def end(self, conversation_id: UUID, now_ms: int) -> WebConversation: ...


class InMemoryWebConversationStore:
    """Thread-safe (per asyncio loop) in-memory backing for tests + studio.

    Real impl writes to ``conversations`` (channel_type='web') with the
    same surface so tests written against this store keep working.
    """

    def __init__(self) -> None:
        self._rows: dict[UUID, WebConversation] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        visitor_id: str,
        now_ms: int,
    ) -> WebConversation:
        if not visitor_id:
            raise ValueError("visitor_id required")
        conv = WebConversation(
            id=uuid4(),
            workspace_id=workspace_id,
            agent_id=agent_id,
            visitor_id=visitor_id,
            started_at_ms=now_ms,
            ended_at_ms=None,
        )
        async with self._lock:
            self._rows[conv.id] = conv
        return conv

    async def get(self, conversation_id: UUID) -> WebConversation:
        async with self._lock:
            row = self._rows.get(conversation_id)
        if row is None:
            raise WebConversationNotFoundError(str(conversation_id))
        return row

    async def append_message(
        self, conversation_id: UUID, message: WebMessage
    ) -> WebConversation:
        async with self._lock:
            row = self._rows.get(conversation_id)
            if row is None:
                raise WebConversationNotFoundError(str(conversation_id))
            if row.ended_at_ms is not None:
                raise ValueError("conversation already ended")
            updated = replace(row, messages=(*row.messages, message))
            self._rows[conversation_id] = updated
            return updated

    async def end(self, conversation_id: UUID, now_ms: int) -> WebConversation:
        async with self._lock:
            row = self._rows.get(conversation_id)
            if row is None:
                raise WebConversationNotFoundError(str(conversation_id))
            if row.ended_at_ms is not None:
                return row
            updated = replace(row, ended_at_ms=now_ms)
            self._rows[conversation_id] = updated
            return updated
