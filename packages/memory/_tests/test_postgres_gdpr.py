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
                "source_trace": params["source_trace"],
                "source_turn_id": params["source_turn_id"],
                "source_span_id": params["source_span_id"],
                "write_reason": params["write_reason"],
                "policy_ref": params["policy_ref"],
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
                "source_trace": params["source_trace"],
                "source_turn_id": params["source_turn_id"],
                "source_span_id": params["source_span_id"],
                "write_reason": params["write_reason"],
                "policy_ref": params["policy_ref"],
            }
            return _Result(rows=[(self._engine.now,)], rowcount=1)
        if "FROM memory_user" in statement and "user_id = :uid AND key = :k" in statement:
            row = self._engine.user_rows.get(
                (params["ws"], params["ag"], params["uid"], params["k"])
            )
            return _Result(rows=[self._value_row(row)] if row else [])
        if "FROM memory_user" in statement and "ORDER BY key" in statement:
            rows = [
                (
                    row["key"],
                    row["value_ciphertext"],
                    row["nonce"],
                    row["algorithm"],
                    row["updated_at"],
                    row["source_trace"],
                    row["source_turn_id"],
                    row["source_span_id"],
                    row["write_reason"],
                    row["policy_ref"],
                )
                for row in sorted(
                    self._engine.user_rows.values(), key=lambda candidate: candidate["key"]
                )
                if row["workspace_id"] == params["ws"]
                and row["agent_id"] == params["ag"]
                and row["user_id"] == params["uid"]
            ]
            return _Result(rows=rows)
        if "FROM memory_user" in statement and "source_trace = :source_trace" in statement:
            rows = [
                (
                    row["user_id"],
                    row["key"],
                    row["value_ciphertext"],
                    row["nonce"],
                    row["algorithm"],
                    row["updated_at"],
                    row["source_trace"],
                    row["source_turn_id"],
                    row["source_span_id"],
                    row["write_reason"],
                    row["policy_ref"],
                )
                for row in sorted(
                    self._engine.user_rows.values(),
                    key=lambda candidate: (candidate["user_id"], candidate["key"]),
                )
                if row["workspace_id"] == params["ws"]
                and row["agent_id"] == params["ag"]
                and (
                    (
                        params["source_trace"] is not None
                        and row["source_trace"] == params["source_trace"]
                    )
                    or (
                        params["source_turn_id"] is not None
                        and row["source_turn_id"] == params["source_turn_id"]
                    )
                )
            ]
            return _Result(rows=rows)
        if "FROM memory_bot" in statement and "key = :k" in statement:
            row = self._engine.bot_rows.get((params["ws"], params["ag"], params["k"]))
            return _Result(rows=[self._value_row(row)] if row else [])
        if "FROM memory_bot" in statement and "source_trace = :source_trace" in statement:
            rows = [
                (
                    row["key"],
                    row["value_ciphertext"],
                    row["nonce"],
                    row["algorithm"],
                    row["updated_at"],
                    row["source_trace"],
                    row["source_turn_id"],
                    row["source_span_id"],
                    row["write_reason"],
                    row["policy_ref"],
                )
                for row in sorted(
                    self._engine.bot_rows.values(), key=lambda candidate: candidate["key"]
                )
                if row["workspace_id"] == params["ws"]
                and row["agent_id"] == params["ag"]
                and (
                    (
                        params["source_trace"] is not None
                        and row["source_trace"] == params["source_trace"]
                    )
                    or (
                        params["source_turn_id"] is not None
                        and row["source_turn_id"] == params["source_turn_id"]
                    )
                )
            ]
            return _Result(rows=rows)
        if "DELETE FROM memory_user" in statement:
            return self._delete_user(statement, params)
        if "DELETE FROM memory_bot" in statement:
            deleted = [
                key
                for key, row in self._engine.bot_rows.items()
                if row["workspace_id"] == params["ws"]
            ]
            for key in deleted:
                self._engine.bot_rows.pop(key)
            return _Result(rowcount=len(deleted))
        raise AssertionError(f"unexpected SQL: {statement}")

    @staticmethod
    def _value_row(row: dict[str, Any] | None) -> tuple[Any, ...]:
        assert row is not None
        return (
            row["value_ciphertext"],
            row["nonce"],
            row["algorithm"],
            row["updated_at"],
            row["source_trace"],
            row["source_turn_id"],
            row["source_span_id"],
            row["write_reason"],
            row["policy_ref"],
        )

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
    assert (
        await store.get_user_or_none(workspace_id=ws, agent_id=ag_a, user_id="u-1", key="a") is None
    )
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
    assert (
        await store.get_user_or_none(workspace_id=ws_a, agent_id=ag, user_id="u", key="a") is None
    )
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
    assert (
        await store.get_user(workspace_id=ws, agent_id=ag, user_id="u", key="profile")
    ).value == {"email": "secret@example.com"}


@pytest.mark.asyncio
async def test_postgres_memory_preserves_source_trace_metadata() -> None:
    engine = _FakeEngine()
    store = PostgresUserMemoryStore(engine, encryption_key=b"5" * 32)  # type: ignore[arg-type]
    ws, ag, turn = uuid4(), uuid4(), uuid4()
    await store.set_user(
        workspace_id=ws,
        agent_id=ag,
        user_id="u",
        key="lang",
        value="English",
        source_trace="trace_lang_001",
        source_turn_id=turn,
        source_span_id="span_memory_write",
        write_reason="User confirmed English preference.",
        policy_ref="memory_policy/user:v1",
    )

    got = await store.get_user(workspace_id=ws, agent_id=ag, user_id="u", key="lang")
    assert got.source_trace == "trace_lang_001"
    assert got.source_turn_id == turn
    assert got.source_span_id == "span_memory_write"
    assert got.write_reason == "User confirmed English preference."
    assert got.policy_ref == "memory_policy/user:v1"

    listed = await store.list_user(workspace_id=ws, agent_id=ag, user_id="u")
    assert listed[0].source_trace == "trace_lang_001"
    assert listed[0].source_turn_id == turn

    await store.set_bot(
        workspace_id=ws,
        agent_id=ag,
        key="persona",
        value={"tone": "plain"},
        source_trace="trace_bot_001",
        write_reason="Builder approved persona.",
    )
    bot = await store.get_bot(workspace_id=ws, agent_id=ag, key="persona")
    assert bot.source_trace == "trace_bot_001"
    assert bot.write_reason == "Builder approved persona."

    by_trace = await store.list_by_source(
        workspace_id=ws,
        agent_id=ag,
        source_trace="trace_lang_001",
    )
    assert [(entry.scope.value, entry.key) for entry in by_trace] == [("user", "lang")]

    by_bot_trace = await store.list_by_source(
        workspace_id=ws,
        agent_id=ag,
        source_trace="trace_bot_001",
    )
    assert [(entry.scope.value, entry.key) for entry in by_bot_trace] == [("bot", "persona")]

    by_turn = await store.list_by_source(
        workspace_id=ws,
        agent_id=ag,
        source_turn_id=turn,
    )
    assert [(entry.scope.value, entry.key) for entry in by_turn] == [("user", "lang")]


@pytest.mark.asyncio
async def test_cross_workspace_isolation_for_same_agent_user_key() -> None:
    engine = _FakeEngine()
    store = PostgresUserMemoryStore(engine, encryption_key=b"4" * 32)  # type: ignore[arg-type]
    ws_a, ws_b, ag = uuid4(), uuid4(), uuid4()
    await store.set_user(workspace_id=ws_a, agent_id=ag, user_id="u", key="lang", value="en")
    await store.set_user(workspace_id=ws_b, agent_id=ag, user_id="u", key="lang", value="fr")

    assert (
        await store.get_user(workspace_id=ws_a, agent_id=ag, user_id="u", key="lang")
    ).value == "en"
    assert (
        await store.get_user(workspace_id=ws_b, agent_id=ag, user_id="u", key="lang")
    ).value == "fr"
