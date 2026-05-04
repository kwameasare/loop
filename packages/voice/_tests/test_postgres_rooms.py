from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from loop_voice.livekit_room import LiveKitAPIClient, RoomGrant
from loop_voice.postgres_rooms import PostgresRoomManager


class FakeLiveKit:
    def __init__(self) -> None:
        self.created: list[str] = []
        self.deleted: list[str] = []

    async def create_room(
        self, *, name: str, empty_timeout_seconds: int, max_participants: int
    ) -> str:
        self.created.append(name)
        return f"SID_{len(self.created)}"

    async def delete_room(self, *, name: str) -> None:
        self.deleted.append(name)

    def mint_token(self, grant: RoomGrant, *, api_key: str, api_secret: str) -> str:
        return f"token:{grant.room}:{grant.identity}:{api_key}:{api_secret}"


class _Result:
    def __init__(self, rows: list[tuple[Any, ...]] | None = None, *, rowcount: int = 0) -> None:
        self._rows = rows or []
        self.rowcount = rowcount

    def first(self) -> tuple[Any, ...] | None:
        return self._rows[0] if self._rows else None

    def all(self) -> list[tuple[Any, ...]]:
        return self._rows


class _Begin:
    def __init__(self, engine: _FakeEngine) -> None:
        self._conn = _Conn(engine)

    async def __aenter__(self) -> _Conn:
        return self._conn

    async def __aexit__(self, *_exc: object) -> None:
        return None


class _Conn:
    def __init__(self, engine: _FakeEngine) -> None:
        self._engine = engine

    async def execute(self, sql: Any, params: dict[str, Any] | None = None) -> _Result:
        statement = str(sql)
        params = params or {}
        if statement.startswith("SET LOCAL"):
            self._engine.active_workspace = UUID(params["ws"])
            return _Result()
        if "INSERT INTO voice_rooms" in statement:
            row = {
                "workspace_id": params["ws"],
                "room_id": params["room_id"],
                "agent_id": params["agent_id"],
                "livekit_room_name": params["name"],
                "started_at": datetime.fromtimestamp(params["started_ms"] / 1000, tz=UTC),
                "ended_at": None,
                "ttl_seconds": params["ttl"],
            }
            self._engine.rows[params["name"]] = row
            return _Result(rowcount=1)
        if "UPDATE voice_rooms" in statement:
            row = self._engine.rows[params["name"]]
            row["ended_at"] = datetime.fromtimestamp(params["ended_ms"] / 1000, tz=UTC)
            return _Result(rowcount=1)
        if "WHERE livekit_room_name = :name" in statement:
            row = self._engine.rows.get(params["name"])
            if row is None or row["ended_at"] is not None:
                return _Result()
            return _Result([self._row(row)])
        if "ORDER BY started_at DESC" in statement:
            rows = [
                self._list_row(row)
                for row in sorted(
                    self._engine.rows.values(),
                    key=lambda candidate: candidate["started_at"],
                    reverse=True,
                )
                if row["workspace_id"] == params["ws"]
            ]
            return _Result(rows[: params["limit"]])
        raise AssertionError(f"unexpected SQL: {statement}")

    @staticmethod
    def _row(row: dict[str, Any]) -> tuple[Any, ...]:
        return (
            row["workspace_id"],
            row["room_id"],
            row["agent_id"],
            row["livekit_room_name"],
            row["started_at"],
            row["ttl_seconds"],
        )

    @staticmethod
    def _list_row(row: dict[str, Any]) -> tuple[Any, ...]:
        return (
            row["room_id"],
            row["livekit_room_name"],
            row["agent_id"],
            row["started_at"],
            row["ttl_seconds"],
        )


class _FakeEngine:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}
        self.active_workspace: UUID | None = None

    def begin(self) -> _Begin:
        return _Begin(self)


@pytest.mark.asyncio
async def test_create_mint_end_list_recent_flow() -> None:
    engine = _FakeEngine()
    client = FakeLiveKit()
    manager = PostgresRoomManager(
        engine=engine,  # type: ignore[arg-type]
        client=client,
        api_key="api-key",
        api_secret="api-secret",
        now_ms=lambda: 1_000,
    )
    workspace_id, agent_id = uuid4(), uuid4()

    room = await manager.create_room(workspace_id=workspace_id, agent_id=agent_id)
    token = manager.mint_participant_token(room=room.name, identity="caller")
    await manager.teardown(room.name)
    recent = await manager.list_recent(workspace_id=workspace_id)

    assert token == f"token:{room.name}:caller:api-key:api-secret"
    assert client.created == [room.name]
    assert client.deleted == [room.name]
    assert [candidate.name for candidate in recent] == [room.name]


def test_livekit_api_client_mints_verifiable_hs256_token() -> None:
    from livekit import api

    secret = "devsecret" * 4
    client = LiveKitAPIClient(url="https://loop.example", api_key="devkey", api_secret=secret)
    token = client.mint_token(
        RoomGrant(
            room="room-a",
            identity="caller-1",
            can_publish=True,
            can_subscribe=False,
            valid_until_ms=4_102_444_800_000,
        ),
        api_key="devkey",
        api_secret=secret,
    )

    claims = api.TokenVerifier("devkey", secret).verify(token)
    assert claims.identity == "caller-1"
    assert claims.video is not None
    assert claims.video.room_join is True
    assert claims.video.room == "room-a"
    assert claims.video.can_publish is True
    assert claims.video.can_subscribe is False
