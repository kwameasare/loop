"""Postgres-backed LiveKit room manager."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from loop_voice.livekit_room import (
    DEFAULT_PARTICIPANT_TTL_SECONDS,
    DEFAULT_ROOM_TTL_SECONDS,
    LiveKitClient,
    LiveKitError,
    Room,
    RoomGrant,
    RoomNotFound,
    _build_room_name,
    now_ms_default,
)

_SET_WS_SQL = text("SET LOCAL loop.workspace_id = :ws")


async def _enter_workspace(conn: AsyncConnection, workspace_id: UUID) -> None:
    await conn.execute(_SET_WS_SQL, {"ws": str(workspace_id)})


class PostgresRoomManager:
    def __init__(
        self,
        *,
        engine: AsyncEngine,
        client: LiveKitClient,
        api_key: str,
        api_secret: str,
        now_ms: Callable[[], int] = now_ms_default,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret required")
        self._engine = engine
        self.client = client
        self.api_key = api_key
        self.api_secret = api_secret
        self.now_ms = now_ms

    async def create_room(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        ttl_seconds: int = DEFAULT_ROOM_TTL_SECONDS,
        max_participants: int = 6,
    ) -> Room:
        if ttl_seconds < 30 or ttl_seconds > 60 * 60 * 4:
            raise ValueError("ttl_seconds out of bounds")
        if max_participants < 2:
            raise ValueError("max_participants must be >=2")
        name = _build_room_name(workspace_id, agent_id)
        try:
            sid = await self.client.create_room(
                name=name,
                empty_timeout_seconds=ttl_seconds,
                max_participants=max_participants,
            )
        except Exception as exc:
            raise LiveKitError(f"create_room failed: {exc}") from exc
        room = Room(
            name=name,
            sid=sid,
            workspace_id=workspace_id,
            agent_id=agent_id,
            created_at_ms=self.now_ms(),
            ttl_seconds=ttl_seconds,
        )
        await self._insert_room(room)
        return room

    def mint_participant_token(
        self,
        *,
        room: str,
        identity: str,
        can_publish: bool = True,
        can_subscribe: bool = True,
        ttl_seconds: int = DEFAULT_PARTICIPANT_TTL_SECONDS,
    ) -> str:
        # The persistent manager cannot synchronously hit Postgres from this
        # existing sync API. Token minting is stateless once callers have the
        # LiveKit room name returned by create_room.
        grant = RoomGrant(
            room=room,
            identity=identity,
            can_publish=can_publish,
            can_subscribe=can_subscribe,
            valid_until_ms=self.now_ms() + ttl_seconds * 1000,
        )
        return self.client.mint_token(grant, api_key=self.api_key, api_secret=self.api_secret)

    async def teardown(self, room_name: str) -> None:
        room = await self._get_by_name(room_name)
        if room is None:
            raise RoomNotFound(f"unknown room {room_name!r}")
        try:
            await self.client.delete_room(name=room_name)
        except Exception as exc:
            raise LiveKitError(f"delete_room failed: {exc}") from exc
        sql = text(
            """
            UPDATE voice_rooms
            SET ended_at = to_timestamp(:ended_ms / 1000.0)
            WHERE workspace_id = :ws AND livekit_room_name = :name
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, room.workspace_id)
            await conn.execute(sql, {"ws": room.workspace_id, "name": room_name, "ended_ms": self.now_ms()})

    async def is_expired(self, room_name: str) -> bool:
        room = await self._get_by_name(room_name)
        if room is None:
            raise RoomNotFound(f"unknown room {room_name!r}")
        return self.now_ms() - room.created_at_ms > room.ttl_seconds * 1000

    async def list_recent(self, *, workspace_id: UUID, limit: int = 20) -> list[Room]:
        sql = text(
            """
            SELECT room_id, livekit_room_name, agent_id, started_at, ttl_seconds
            FROM voice_rooms
            WHERE workspace_id = :ws
            ORDER BY started_at DESC
            LIMIT :limit
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, workspace_id)
            rows = (await conn.execute(sql, {"ws": workspace_id, "limit": limit})).all()
        return [
            Room(
                sid=str(row[0]),
                name=str(row[1]),
                workspace_id=workspace_id,
                agent_id=_coerce_uuid(row[2]),
                created_at_ms=_dt_to_ms(row[3]),
                ttl_seconds=int(row[4]),
            )
            for row in rows
        ]

    async def _insert_room(self, room: Room) -> None:
        sql = text(
            """
            INSERT INTO voice_rooms
                (workspace_id, room_id, agent_id, livekit_room_name, started_at, ttl_seconds)
            VALUES (:ws, :room_id, :agent_id, :name, to_timestamp(:started_ms / 1000.0), :ttl)
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, room.workspace_id)
            await conn.execute(
                sql,
                {
                    "ws": room.workspace_id,
                    "room_id": room.sid,
                    "agent_id": room.agent_id,
                    "name": room.name,
                    "started_ms": room.created_at_ms,
                    "ttl": room.ttl_seconds,
                },
            )

    async def _get_by_name(self, room_name: str) -> Room | None:
        sql = text(
            """
            SELECT workspace_id, room_id, agent_id, livekit_room_name, started_at, ttl_seconds
            FROM voice_rooms
            WHERE livekit_room_name = :name AND ended_at IS NULL
            """
        )
        async with self._engine.begin() as conn:
            row = (await conn.execute(sql, {"name": room_name})).first()
        if row is None:
            return None
        return Room(
            workspace_id=_coerce_uuid(row[0]),
            sid=str(row[1]),
            agent_id=_coerce_uuid(row[2]),
            name=str(row[3]),
            created_at_ms=_dt_to_ms(row[4]),
            ttl_seconds=int(row[5]),
        )


def _coerce_uuid(value: object) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _dt_to_ms(value: object) -> int:
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=UTC)
        return int(dt.timestamp() * 1000)
    return int(value)


__all__ = ["PostgresRoomManager"]
