"""Postgres-backed provider-user to conversation_id index."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

_SET_WS_SQL = text("SET LOCAL loop.workspace_id = :ws")


async def _enter_workspace(conn: AsyncConnection, workspace_id: UUID) -> None:
    await conn.execute(_SET_WS_SQL, {"ws": str(workspace_id)})


class PostgresConversationIndex:
    """Generic persistent conversation index for channel adapters."""

    def __init__(self, engine: AsyncEngine, *, workspace_id: UUID, channel: str) -> None:
        if not channel:
            raise ValueError("channel is required")
        self._engine = engine
        self._workspace_id = workspace_id
        self._channel = channel

    async def get_or_create(self, *, provider_user_id: str) -> UUID:
        conversation_id = uuid4()
        sql = text(
            """
            INSERT INTO channel_conversation_index
                (workspace_id, channel, provider_user_id, conversation_id, last_seen_at)
            VALUES (:ws, :channel, :provider_user_id, :conversation_id, now())
            ON CONFLICT (workspace_id, channel, provider_user_id)
            DO UPDATE SET last_seen_at = now()
            RETURNING conversation_id
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, self._workspace_id)
            row = (
                await conn.execute(
                    sql,
                    {
                        "ws": self._workspace_id,
                        "channel": self._channel,
                        "provider_user_id": provider_user_id,
                        "conversation_id": conversation_id,
                    },
                )
            ).first()
        return _coerce_uuid(row[0]) if row is not None else conversation_id

    async def get(self, *, provider_user_id: str) -> UUID | None:
        sql = text(
            """
            SELECT conversation_id
            FROM channel_conversation_index
            WHERE workspace_id = :ws
              AND channel = :channel
              AND provider_user_id = :provider_user_id
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, self._workspace_id)
            row = (
                await conn.execute(
                    sql,
                    {
                        "ws": self._workspace_id,
                        "channel": self._channel,
                        "provider_user_id": provider_user_id,
                    },
                )
            ).first()
        return _coerce_uuid(row[0]) if row is not None else None


def _coerce_uuid(value: object) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


__all__ = ["PostgresConversationIndex"]
