from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from loop_channels_core.conversation_index_postgres import PostgresConversationIndex


class _Result:
    def __init__(self, rows: list[tuple[Any, ...]] | None = None, *, rowcount: int = 0) -> None:
        self._rows = rows or []
        self.rowcount = rowcount

    def first(self) -> tuple[Any, ...] | None:
        return self._rows[0] if self._rows else None


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
        key = (params["ws"], params["channel"], params["provider_user_id"])
        if "INSERT INTO channel_conversation_index" in statement:
            row = self._engine.rows.setdefault(
                key,
                {
                    "conversation_id": params["conversation_id"],
                    "last_seen_at": self._engine.now,
                },
            )
            row["last_seen_at"] = self._engine.now
            return _Result([(row["conversation_id"],)], rowcount=1)
        if "SELECT conversation_id" in statement:
            row = self._engine.rows.get(key)
            return _Result([(row["conversation_id"],)] if row else [])
        raise AssertionError(f"unexpected SQL: {statement}")


class _FakeEngine:
    def __init__(self) -> None:
        self.rows: dict[tuple[UUID, str, str], dict[str, Any]] = {}
        self.active_workspace: UUID | None = None
        self.now = datetime(2026, 5, 4, 12, 0, tzinfo=UTC)

    def begin(self) -> _Begin:
        return _Begin(self)


@pytest.mark.asyncio
async def test_insert_then_lookup() -> None:
    engine = _FakeEngine()
    ws = uuid4()
    index = PostgresConversationIndex(engine, workspace_id=ws, channel="whatsapp")  # type: ignore[arg-type]

    conversation_id = await index.get_or_create(provider_user_id="+15551234567")

    assert await index.get(provider_user_id="+15551234567") == conversation_id


@pytest.mark.asyncio
async def test_cross_channel_isolation() -> None:
    engine = _FakeEngine()
    ws = uuid4()
    whatsapp = PostgresConversationIndex(engine, workspace_id=ws, channel="whatsapp")  # type: ignore[arg-type]
    discord = PostgresConversationIndex(engine, workspace_id=ws, channel="discord")  # type: ignore[arg-type]

    wa_id = await whatsapp.get_or_create(provider_user_id="+15551234567")
    discord_id = await discord.get_or_create(provider_user_id="+15551234567")

    assert wa_id != discord_id
    assert await whatsapp.get(provider_user_id="+15551234567") == wa_id
    assert await discord.get(provider_user_id="+15551234567") == discord_id


@pytest.mark.asyncio
async def test_restart_survival() -> None:
    engine = _FakeEngine()
    ws = uuid4()
    first = PostgresConversationIndex(engine, workspace_id=ws, channel="slack")  # type: ignore[arg-type]
    conversation_id = await first.get_or_create(provider_user_id="T1:123.4")

    restarted = PostgresConversationIndex(engine, workspace_id=ws, channel="slack")  # type: ignore[arg-type]

    assert await restarted.get(provider_user_id="T1:123.4") == conversation_id


@pytest.mark.asyncio
async def test_duplicate_get_or_create_is_idempotent() -> None:
    engine = _FakeEngine()
    ws = uuid4()
    index = PostgresConversationIndex(engine, workspace_id=ws, channel="teams")  # type: ignore[arg-type]

    first = await index.get_or_create(provider_user_id="conversation-ref")
    second = await index.get_or_create(provider_user_id="conversation-ref")

    assert second == first
    assert len(engine.rows) == 1
