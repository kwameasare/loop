"""Process-local memory stores for tests and the dev studio.

Both implementations are deliberately simple: they hold a dict keyed
on the same composite tuple as the underlying Postgres / Redis row.
They are safe to use concurrently from a single asyncio event loop
because every operation is synchronous-on-await.
"""

from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from loop_memory.models import MemoryEntry, MemoryScope
from loop_memory.stores import MemoryNotFoundError

_UserKey = tuple[UUID, UUID, str, str]  # workspace, agent, user, key
_BotKey = tuple[UUID, UUID, str]  # workspace, agent, key


class InMemoryUserMemoryStore:
    """``UserMemoryStore`` impl backed by two dicts.

    Values are deep-copied on set/get so callers cannot mutate stored
    state through aliasing -- mirrors how Postgres ``JSONB`` works.
    """

    def __init__(self) -> None:
        self._user: dict[_UserKey, MemoryEntry] = {}
        self._bot: dict[_BotKey, MemoryEntry] = {}
        self._lock = asyncio.Lock()

    # -- user ----------------------------------------------------------------

    async def get_user(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: str,
        key: str,
    ) -> MemoryEntry:
        entry = await self.get_user_or_none(
            workspace_id=workspace_id,
            agent_id=agent_id,
            user_id=user_id,
            key=key,
        )
        if entry is None:
            raise MemoryNotFoundError(
                f"user memory not found: workspace={workspace_id} "
                f"agent={agent_id} user={user_id} key={key!r}"
            )
        return entry

    async def get_user_or_none(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: str,
        key: str,
    ) -> MemoryEntry | None:
        async with self._lock:
            return self._user.get((workspace_id, agent_id, user_id, key))

    async def set_user(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: str,
        key: str,
        value: Any,
        source_trace: str = "",
        source_turn_id: UUID | None = None,
        source_span_id: str = "",
        write_reason: str = "",
        policy_ref: str = "",
    ) -> MemoryEntry:
        entry = MemoryEntry(
            workspace_id=workspace_id,
            agent_id=agent_id,
            scope=MemoryScope.USER,
            user_id=user_id,
            key=key,
            value=deepcopy(value),
            updated_at=datetime.now(UTC),
            source_trace=source_trace,
            source_turn_id=source_turn_id,
            source_span_id=source_span_id,
            write_reason=write_reason,
            policy_ref=policy_ref,
        )
        async with self._lock:
            self._user[(workspace_id, agent_id, user_id, key)] = entry
        return entry

    async def delete_user(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: str,
        key: str,
    ) -> bool:
        async with self._lock:
            return self._user.pop((workspace_id, agent_id, user_id, key), None) is not None

    async def list_user(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: str,
    ) -> list[MemoryEntry]:
        async with self._lock:
            return [
                e
                for (ws, ag, uid, _), e in self._user.items()
                if ws == workspace_id and ag == agent_id and uid == user_id
            ]

    async def list_by_source(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        source_trace: str | None = None,
        source_turn_id: UUID | None = None,
    ) -> list[MemoryEntry]:
        if not source_trace and source_turn_id is None:
            return []
        async with self._lock:
            entries = [
                e
                for (ws, ag, _, _), e in self._user.items()
                if ws == workspace_id and ag == agent_id
            ]
            entries.extend(
                e for (ws, ag, _), e in self._bot.items() if ws == workspace_id and ag == agent_id
            )
        return [
            e
            for e in entries
            if (source_trace and e.source_trace == source_trace)
            or (source_turn_id is not None and e.source_turn_id == source_turn_id)
        ]

    # -- bot -----------------------------------------------------------------

    async def get_bot(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        key: str,
    ) -> MemoryEntry:
        entry = await self.get_bot_or_none(workspace_id=workspace_id, agent_id=agent_id, key=key)
        if entry is None:
            raise MemoryNotFoundError(
                f"bot memory not found: workspace={workspace_id} agent={agent_id} key={key!r}"
            )
        return entry

    async def get_bot_or_none(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        key: str,
    ) -> MemoryEntry | None:
        async with self._lock:
            return self._bot.get((workspace_id, agent_id, key))

    async def set_bot(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        key: str,
        value: Any,
        source_trace: str = "",
        source_turn_id: UUID | None = None,
        source_span_id: str = "",
        write_reason: str = "",
        policy_ref: str = "",
    ) -> MemoryEntry:
        entry = MemoryEntry(
            workspace_id=workspace_id,
            agent_id=agent_id,
            scope=MemoryScope.BOT,
            key=key,
            value=deepcopy(value),
            updated_at=datetime.now(UTC),
            source_trace=source_trace,
            source_turn_id=source_turn_id,
            source_span_id=source_span_id,
            write_reason=write_reason,
            policy_ref=policy_ref,
        )
        async with self._lock:
            self._bot[(workspace_id, agent_id, key)] = entry
        return entry


class InMemorySessionMemoryStore:
    """``SessionMemoryStore`` impl backed by a per-conversation dict."""

    def __init__(self) -> None:
        self._sessions: dict[UUID, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, *, conversation_id: UUID, key: str) -> Any | None:
        async with self._lock:
            return deepcopy(self._sessions.get(conversation_id, {}).get(key))

    async def set(self, *, conversation_id: UUID, key: str, value: Any) -> None:
        async with self._lock:
            self._sessions.setdefault(conversation_id, {})[key] = deepcopy(value)

    async def delete(self, *, conversation_id: UUID, key: str) -> bool:
        async with self._lock:
            session = self._sessions.get(conversation_id)
            if not session:
                return False
            return session.pop(key, None) is not None

    async def all(self, *, conversation_id: UUID) -> dict[str, Any]:
        async with self._lock:
            return deepcopy(self._sessions.get(conversation_id, {}))

    async def clear(self, *, conversation_id: UUID) -> None:
        async with self._lock:
            self._sessions.pop(conversation_id, None)


__all__ = ["InMemorySessionMemoryStore", "InMemoryUserMemoryStore"]
