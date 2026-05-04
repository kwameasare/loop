from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from loop_memory.postgres import MAX_VALUE_BYTES, PostgresUserMemoryStore


class _Result:
    def __init__(
        self,
        *,
        rows: Iterable[tuple[Any, ...]] = (),
        rowcount: int = 0,
    ) -> None:
        self._rows = list(rows)
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
        if "INSERT INTO memory_user" in statement:
            key = (params["ws"], params["ag"], params["uid"], params["k"])
            self._engine.user_rows[key] = {
                "workspace_id": params["ws"],
                "agent_id": params["ag"],
                "user_id": params["uid"],
                "key": params["k"],
                "value_ciphertext": params["ciphertext"],
                "nonce": params["nonce"],
                "algorithm": params["algorithm"],
                "updated_at": self._engine.now,
            }
            return _Result(rows=[(self._engine.now,)], rowcount=1)
        if "INSERT INTO memory_bot" in statement:
            key = (params["ws"], params["ag"], params["k"])
            self._engine.bot_rows[key] = {
                "workspace_id": params["ws"],
                "agent_id": params["ag"],
                "key": params["k"],
                "value_ciphertext": params["ciphertext"],
                "nonce": params["nonce"],
                "algorithm": params["algorithm"],
                "updated_at": self._engine.now,
            }
            return _Result(rows=[(self._engine.now,)], rowcount=1)
        if "SELECT value_ciphertext, nonce, algorithm, updated_at FROM memory_user" in statement:
            row = self._engine.user_rows.get((params["ws"], params["ag"], params["uid"], params["k"]))
            return _Result(rows=[self._value_row(row)] if row else [])
        if "SELECT key, value_ciphertext, nonce, algorithm, updated_at FROM memory_user" in statement:
            rows = [
                (
                    row["key"],
                    row["value_ciphertext"],
                    row["nonce"],
                    row["algorithm"],
                    row["updated_at"],
                )
                for row in sorted(self._engine.user_rows.values(), key=lambda candidate: candidate["key"])
                if row["workspace_id"] == params["ws"]
                and row["agent_id"] == params["ag"]
                and row["user_id"] == params["uid"]
            ]
            return _Result(rows=rows)
        if "SELECT value_ciphertext, nonce, algorithm, updated_at FROM memory_bot" in statement:
            row = self._engine.bot_rows.get((params["ws"], params["ag"], params["k"]))
            return _Result(rows=[self._value_row(row)] if row else [])
        if "DELETE FROM memory_user" in statement:
            return self._delete_user(statement, params)
        if "DELETE FROM memory_bot" in statement:
            deleted = [
                key for key, row in self._engine.bot_rows.items() if row["workspace_id"] == params["ws"]
            ]
            for key in deleted:
                self._engine.bot_rows.pop(key)
            return _Result(rowcount=len(deleted))
        raise AssertionError(f"unexpected SQL: {statement}")

    @staticmethod
    def _value_row(row: dict[str, Any] | None) -> tuple[Any, ...]:
        assert row is not None
        return (row["value_ciphertext"], row["nonce"], row["algorithm"], row["updated_at"])

    def _delete_user(self, statement: str, params: dict[str, Any]) -> _Result:
        if "agent_id = :ag" in statement and "key = :k" in statement:
            key = (params["ws"], params["ag"], params["uid"], params["k"])
            existed = self._engine.user_rows.pop(key, None) is not None
            return _Result(rowcount=1 if existed else 0)
        deleted = [
            key
            for key, row in self._engine.user_rows.items()
            if row["workspace_id"] == params["ws"]
            and ("uid" not in params or row["user_id"] == params["uid"])
        ]
        for key in deleted:
            self._engine.user_rows.pop(key)
        return _Result(rowcount=len(deleted))


class _FakeEngine:
    def __init__(self) -> None:
        self.user_rows: dict[tuple[UUID, UUID, str, str], dict[str, Any]] = {}
        self.bot_rows: dict[tuple[UUID, UUID, str], dict[str, Any]] = {}
        self.active_workspace: UUID | None = None
        self.now = datetime(2026, 5, 4, 12, 0, tzinfo=UTC)

    def begin(self) -> _Begin:
        return _Begin(self)


@pytest.mark.asyncio
async def test_delete_all_for_user_removes_every_user_key_and_is_idempotent() -> None:
    engine = _FakeEngine()
    store = PostgresUserMemoryStore(engine, encryption_key=b"0" * 32)  # type: ignore[arg-type]
    ws, ag_a, ag_b = uuid4(), uuid4(), uuid4()
    await store.set_user(workspace_id=ws, agent_id=ag_a, user_id="u-1", key="a", value=1)
    await store.set_user(workspace_id=ws, agent_id=ag_b, user_id="u-1", key="b", value=2)
    await store.set_user(workspace_id=ws, agent_id=ag_a, user_id="u-2", key="a", value=3)

    assert await store.delete_all_for_user(workspace_id=ws, user_id="u-1") == 2
    assert await store.delete_all_for_user(workspace_id=ws, user_id="u-1") == 0
    assert await store.get_user_or_none(workspace_id=ws, agent_id=ag_a, user_id="u-1", key="a") is None
    assert (await store.get_user(workspace_id=ws, agent_id=ag_a, user_id="u-2", key="a")).value == 3


@pytest.mark.asyncio
async def test_delete_all_for_workspace_removes_user_and_bot_memory() -> None:
    engine = _FakeEngine()
    store = PostgresUserMemoryStore(engine, encryption_key=b"1" * 32)  # type: ignore[arg-type]
    ws_a, ws_b, ag = uuid4(), uuid4(), uuid4()
    await store.set_user(workspace_id=ws_a, agent_id=ag, user_id="u", key="a", value=1)
    await store.set_bot(workspace_id=ws_a, agent_id=ag, key="persona", value={"tone": "plain"})
    await store.set_user(workspace_id=ws_b, agent_id=ag, user_id="u", key="a", value=2)

    assert await store.delete_all_for_workspace(ws_a) == 2
    assert await store.delete_all_for_workspace(ws_a) == 0
    assert await store.get_user_or_none(workspace_id=ws_a, agent_id=ag, user_id="u", key="a") is None
    assert (await store.get_user(workspace_id=ws_b, agent_id=ag, user_id="u", key="a")).value == 2


@pytest.mark.asyncio
async def test_set_rejects_values_over_64kib() -> None:
    store = PostgresUserMemoryStore(_FakeEngine(), encryption_key=b"2" * 32)  # type: ignore[arg-type]
    with pytest.raises(MemoryError, match="value exceeds 64 KiB"):
        await store.set_user(
            workspace_id=uuid4(),
            agent_id=uuid4(),
            user_id="u",
            key="blob",
            value="x" * (MAX_VALUE_BYTES + 1),
        )


@pytest.mark.asyncio
async def test_encrypted_round_trip_does_not_store_plaintext_json() -> None:
    engine = _FakeEngine()
    store = PostgresUserMemoryStore(engine, encryption_key=b"3" * 32)  # type: ignore[arg-type]
    ws, ag = uuid4(), uuid4()
    await store.set_user(
        workspace_id=ws,
        agent_id=ag,
        user_id="u",
        key="profile",
        value={"email": "secret@example.com"},
    )

    row = next(iter(engine.user_rows.values()))
    assert b"secret@example.com" not in row["value_ciphertext"]
    assert row["nonce"]
    assert row["algorithm"] == "loop.memory.aesgcm.v1"
    assert (await store.get_user(workspace_id=ws, agent_id=ag, user_id="u", key="profile")).value == {
        "email": "secret@example.com"
    }


@pytest.mark.asyncio
async def test_cross_workspace_isolation_for_same_agent_user_key() -> None:
    engine = _FakeEngine()
    store = PostgresUserMemoryStore(engine, encryption_key=b"4" * 32)  # type: ignore[arg-type]
    ws_a, ws_b, ag = uuid4(), uuid4(), uuid4()
    await store.set_user(workspace_id=ws_a, agent_id=ag, user_id="u", key="lang", value="en")
    await store.set_user(workspace_id=ws_b, agent_id=ag, user_id="u", key="lang", value="fr")

    assert (await store.get_user(workspace_id=ws_a, agent_id=ag, user_id="u", key="lang")).value == "en"
    assert (await store.get_user(workspace_id=ws_b, agent_id=ag, user_id="u", key="lang")).value == "fr"
