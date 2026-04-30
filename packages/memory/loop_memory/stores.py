"""Memory store protocols.

The runtime depends on these abstract interfaces, not on the concrete
Postgres or Redis adapters. That keeps the hot path testable and makes
swapping in a fake or a future cache layer (memcached for session,
DynamoDB for user) a typing change rather than a refactor.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from loop_memory.models import MemoryEntry


class MemoryNotFoundError(KeyError):
    """Raised by ``get`` style accessors when a key is absent.

    Callers that prefer ``None`` should use ``get_or_none``.
    """


class UserMemoryStore(Protocol):
    """Persistent user/bot memory backed by Postgres ``memory_user`` /
    ``memory_bot`` tables.

    Implementations must be safe to share across tasks within a single
    workspace context; tenancy is enforced at write time via the
    explicit ``workspace_id`` argument plus the underlying RLS policy.
    """

    async def get_user(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: str,
        key: str,
    ) -> MemoryEntry: ...

    async def get_user_or_none(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: str,
        key: str,
    ) -> MemoryEntry | None: ...

    async def set_user(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: str,
        key: str,
        value: Any,
    ) -> MemoryEntry: ...

    async def delete_user(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: str,
        key: str,
    ) -> bool: ...

    async def list_user(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: str,
    ) -> list[MemoryEntry]: ...

    async def get_bot(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        key: str,
    ) -> MemoryEntry: ...

    async def get_bot_or_none(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        key: str,
    ) -> MemoryEntry | None: ...

    async def set_bot(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        key: str,
        value: Any,
    ) -> MemoryEntry: ...


class SessionMemoryStore(Protocol):
    """Per-conversation ephemeral memory backed by Redis.

    Keys live under ``loop:session:{conversation_id}:{key}`` with a
    configurable TTL (default 24h, per SCHEMA.md §5). Setting any key
    refreshes the TTL on the whole conversation hash so an active
    conversation never loses session state mid-turn.
    """

    async def get(
        self, *, conversation_id: UUID, key: str
    ) -> Any | None: ...

    async def set(
        self,
        *,
        conversation_id: UUID,
        key: str,
        value: Any,
    ) -> None: ...

    async def delete(
        self, *, conversation_id: UUID, key: str
    ) -> bool: ...

    async def all(self, *, conversation_id: UUID) -> dict[str, Any]: ...

    async def clear(self, *, conversation_id: UUID) -> None: ...


__all__ = ["MemoryNotFoundError", "SessionMemoryStore", "UserMemoryStore"]
