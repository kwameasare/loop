"""Postgres adapter for user/bot memory.

Backs ``memory_user`` and ``memory_bot`` (SCHEMA.md §3.2). Uses
SQLAlchemy 2.0 Core async to keep the dependency surface small (we
don't need ORM mappings for two tables of two value columns).

Tenancy is enforced two ways:

1. Every statement filters by ``workspace_id``.
2. Every operation opens its own transaction and executes
   ``SET LOCAL loop.workspace_id = '<uuid>'`` **before** any data
   query, so the data-plane RLS policy (``FORCE ROW LEVEL SECURITY``
   from dp_0001) double-checks at the database level.

   Without that ``SET LOCAL``, ``current_setting('loop.workspace_id',
   true)`` returns NULL, the policy ``USING (workspace_id = ...)``
   evaluates to NULL → row filtered out, and **every read returns
   zero rows**. Always set the GUC first.

Conflict-on-insert uses ``ON CONFLICT ... DO UPDATE`` so concurrent
writers converge on last-write-wins by ``updated_at``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from loop_memory.models import MemoryEntry, MemoryScope
from loop_memory.stores import MemoryNotFoundError

# `SET LOCAL` must be issued inside an explicit transaction; that's why
# every operation below uses ``engine.begin()`` (never ``engine.connect()``)
# and routes through this helper.
_SET_WS_SQL = text("SET LOCAL loop.workspace_id = :ws")


async def _enter_workspace(conn: AsyncConnection, workspace_id: UUID) -> None:
    """Bind ``loop.workspace_id`` for the lifetime of this transaction."""
    await conn.execute(_SET_WS_SQL, {"ws": str(workspace_id)})


class PostgresUserMemoryStore:
    """``UserMemoryStore`` implementation against the data-plane Postgres."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    # -- user ---------------------------------------------------------------

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
        sql = text(
            """
            SELECT value_json, updated_at FROM memory_user
            WHERE workspace_id = :ws AND agent_id = :ag
              AND user_id = :uid AND key = :k
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, workspace_id)
            row = (
                await conn.execute(
                    sql,
                    {"ws": workspace_id, "ag": agent_id, "uid": user_id, "k": key},
                )
            ).first()
        if row is None:
            return None
        value, updated = _decode_row(row)
        return MemoryEntry(
            workspace_id=workspace_id,
            agent_id=agent_id,
            scope=MemoryScope.USER,
            user_id=user_id,
            key=key,
            value=value,
            updated_at=updated,
        )

    async def set_user(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: str,
        key: str,
        value: Any,
    ) -> MemoryEntry:
        sql = text(
            """
            INSERT INTO memory_user
                (workspace_id, agent_id, user_id, key, value_json, updated_at)
            VALUES (:ws, :ag, :uid, :k, CAST(:v AS jsonb), now())
            ON CONFLICT (workspace_id, agent_id, user_id, key)
            DO UPDATE SET value_json = EXCLUDED.value_json,
                          updated_at = EXCLUDED.updated_at
            RETURNING updated_at
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, workspace_id)
            row = (
                await conn.execute(
                    sql,
                    {
                        "ws": workspace_id,
                        "ag": agent_id,
                        "uid": user_id,
                        "k": key,
                        "v": json.dumps(value, default=str),
                    },
                )
            ).first()
        updated = _coerce_dt(row[0]) if row is not None else datetime.now(UTC)
        return MemoryEntry(
            workspace_id=workspace_id,
            agent_id=agent_id,
            scope=MemoryScope.USER,
            user_id=user_id,
            key=key,
            value=value,
            updated_at=updated,
        )

    async def delete_user(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: str,
        key: str,
    ) -> bool:
        sql = text(
            """
            DELETE FROM memory_user
            WHERE workspace_id = :ws AND agent_id = :ag
              AND user_id = :uid AND key = :k
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, workspace_id)
            result = await conn.execute(
                sql,
                {"ws": workspace_id, "ag": agent_id, "uid": user_id, "k": key},
            )
        return result.rowcount > 0

    async def list_user(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: str,
    ) -> list[MemoryEntry]:
        sql = text(
            """
            SELECT key, value_json, updated_at FROM memory_user
            WHERE workspace_id = :ws AND agent_id = :ag AND user_id = :uid
            ORDER BY key
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, workspace_id)
            rows = (
                await conn.execute(sql, {"ws": workspace_id, "ag": agent_id, "uid": user_id})
            ).all()
        out: list[MemoryEntry] = []
        for k, raw_value, updated in rows:
            value = _decode_value(raw_value)
            out.append(
                MemoryEntry(
                    workspace_id=workspace_id,
                    agent_id=agent_id,
                    scope=MemoryScope.USER,
                    user_id=user_id,
                    key=k,
                    value=value,
                    updated_at=_coerce_dt(updated),
                )
            )
        return out

    # -- bot ----------------------------------------------------------------

    async def get_bot(self, *, workspace_id: UUID, agent_id: UUID, key: str) -> MemoryEntry:
        entry = await self.get_bot_or_none(workspace_id=workspace_id, agent_id=agent_id, key=key)
        if entry is None:
            raise MemoryNotFoundError(
                f"bot memory not found: workspace={workspace_id} agent={agent_id} key={key!r}"
            )
        return entry

    async def get_bot_or_none(
        self, *, workspace_id: UUID, agent_id: UUID, key: str
    ) -> MemoryEntry | None:
        sql = text(
            """
            SELECT value_json, updated_at FROM memory_bot
            WHERE workspace_id = :ws AND agent_id = :ag AND key = :k
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, workspace_id)
            row = (await conn.execute(sql, {"ws": workspace_id, "ag": agent_id, "k": key})).first()
        if row is None:
            return None
        value, updated = _decode_row(row)
        return MemoryEntry(
            workspace_id=workspace_id,
            agent_id=agent_id,
            scope=MemoryScope.BOT,
            key=key,
            value=value,
            updated_at=updated,
        )

    async def set_bot(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        key: str,
        value: Any,
    ) -> MemoryEntry:
        sql = text(
            """
            INSERT INTO memory_bot
                (workspace_id, agent_id, key, value_json, updated_at)
            VALUES (:ws, :ag, :k, CAST(:v AS jsonb), now())
            ON CONFLICT (workspace_id, agent_id, key)
            DO UPDATE SET value_json = EXCLUDED.value_json,
                          updated_at = EXCLUDED.updated_at
            RETURNING updated_at
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, workspace_id)
            row = (
                await conn.execute(
                    sql,
                    {
                        "ws": workspace_id,
                        "ag": agent_id,
                        "k": key,
                        "v": json.dumps(value, default=str),
                    },
                )
            ).first()
        updated = _coerce_dt(row[0]) if row is not None else datetime.now(UTC)
        return MemoryEntry(
            workspace_id=workspace_id,
            agent_id=agent_id,
            scope=MemoryScope.BOT,
            key=key,
            value=value,
            updated_at=updated,
        )


def _decode_row(row: Any) -> tuple[Any, datetime]:
    raw_value, updated = row[0], row[1]
    return _decode_value(raw_value), _coerce_dt(updated)


def _decode_value(raw: Any) -> Any:
    """JSONB columns may surface as already-decoded objects (psycopg)
    or as raw JSON strings (asyncpg, depending on type codec)."""
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return raw


def _coerce_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.now(UTC)


__all__ = ["PostgresUserMemoryStore"]
