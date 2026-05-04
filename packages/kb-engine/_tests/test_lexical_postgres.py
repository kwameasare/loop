from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from loop_kb_engine.lexical_postgres import PostgresLexicalIndex


class _Result:
    def __init__(self, *, rows: Iterable[tuple[Any, ...]] = (), rowcount: int = 0) -> None:
        self._rows = list(rows)
        self.rowcount = rowcount

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
        if "INSERT INTO kb_lexical_index" in statement:
            self._engine.rows[(params["ws"], params["doc_id"])] = {
                "workspace_id": params["ws"],
                "doc_id": params["doc_id"],
                "terms": params["terms"],
                "updated_at": self._engine.now,
            }
            return _Result(rowcount=1)
        if "SELECT doc_id" in statement and "FROM kb_lexical_index" in statement:
            query_terms = _tokens(params["query"])
            scored = []
            for row in self._engine.rows.values():
                if row["workspace_id"] != params["ws"]:
                    continue
                terms = _tokens(row["terms"])
                score = float(len(query_terms & terms))
                if score > 0:
                    scored.append((row["doc_id"], score))
            scored.sort(key=lambda pair: (-pair[1], str(pair[0])))
            return _Result(rows=scored[: params["k"]])
        if "DELETE FROM kb_lexical_index" in statement:
            existed = self._engine.rows.pop((params["ws"], params["doc_id"]), None) is not None
            return _Result(rowcount=1 if existed else 0)
        raise AssertionError(f"unexpected SQL: {statement}")


class _FakeEngine:
    def __init__(self) -> None:
        self.rows: dict[tuple[UUID, UUID], dict[str, Any]] = {}
        self.active_workspace: UUID | None = None
        self.now = datetime(2026, 5, 4, 12, 0, tzinfo=UTC)

    def begin(self) -> _Begin:
        return _Begin(self)


def _tokens(value: str) -> set[str]:
    return {part.lower() for part in value.split() if part}


@pytest.mark.asyncio
async def test_index_then_query_returns_document() -> None:
    ws = uuid4()
    doc_id = uuid4()
    index = PostgresLexicalIndex(_FakeEngine(), workspace_id=ws)  # type: ignore[arg-type]

    await index.index(doc_id, ["postgres", "gin", "lexical"])
    hits = await index.search("postgres", k=5)

    assert [hit.doc_id for hit in hits] == [doc_id]
    assert hits[0].score > 0


@pytest.mark.asyncio
async def test_cross_workspace_isolation() -> None:
    engine = _FakeEngine()
    ws_a, ws_b = uuid4(), uuid4()
    doc_a, doc_b = uuid4(), uuid4()
    index_a = PostgresLexicalIndex(engine, workspace_id=ws_a)  # type: ignore[arg-type]
    index_b = PostgresLexicalIndex(engine, workspace_id=ws_b)  # type: ignore[arg-type]

    await index_a.index(doc_a, "tenant secret alpha")
    await index_b.index(doc_b, "tenant secret beta")

    assert [hit.doc_id for hit in await index_a.search("alpha", k=5)] == [doc_a]
    assert await index_b.search("alpha", k=5) == []


@pytest.mark.asyncio
async def test_delete_removes_document_from_index() -> None:
    engine = _FakeEngine()
    ws = uuid4()
    doc_id = uuid4()
    index = PostgresLexicalIndex(engine, workspace_id=ws)  # type: ignore[arg-type]
    await index.index(doc_id, "removable content")

    assert await index.delete(doc_id)
    assert not await index.delete(doc_id)
    assert await index.search("removable", k=5) == []


@pytest.mark.asyncio
async def test_restart_survival_uses_existing_database_rows() -> None:
    engine = _FakeEngine()
    ws = uuid4()
    doc_id = uuid4()
    first = PostgresLexicalIndex(engine, workspace_id=ws)  # type: ignore[arg-type]
    await first.index(doc_id, "survives restart")

    restarted = PostgresLexicalIndex(engine, workspace_id=ws)  # type: ignore[arg-type]
    assert [hit.doc_id for hit in await restarted.search("restart", k=5)] == [doc_id]
