"""Postgres-backed lexical index for KB BM25-style retrieval.

The index is workspace-scoped at construction time, matching the
in-memory shape used by the KB engine: callers index a document/chunk id
with lexical terms, search a query, and delete ids when documents are
tombstoned. Postgres owns persistence and ranking through ``tsvector``,
``GIN`` and ``ts_rank_cd``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

_SET_WS_SQL = text("SET LOCAL loop.workspace_id = :ws")


@dataclass(frozen=True)
class LexicalHit:
    doc_id: UUID
    score: float


async def _enter_workspace(conn: AsyncConnection, workspace_id: UUID) -> None:
    await conn.execute(_SET_WS_SQL, {"ws": str(workspace_id)})


class PostgresLexicalIndex:
    """Workspace-isolated ``tsvector`` lexical index."""

    def __init__(self, engine: AsyncEngine, *, workspace_id: UUID) -> None:
        self._engine = engine
        self._workspace_id = workspace_id

    async def index(self, doc_id: UUID, terms: str | Iterable[str]) -> None:
        body = _normalise_terms(terms)
        sql = text(
            """
            INSERT INTO kb_lexical_index (workspace_id, doc_id, terms, updated_at)
            VALUES (:ws, :doc_id, :terms, now())
            ON CONFLICT (workspace_id, doc_id)
            DO UPDATE SET terms = EXCLUDED.terms,
                          updated_at = EXCLUDED.updated_at
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, self._workspace_id)
            await conn.execute(
                sql,
                {"ws": self._workspace_id, "doc_id": doc_id, "terms": body},
            )

    async def search(self, query: str | Iterable[str], k: int = 10) -> list[LexicalHit]:
        if k <= 0:
            return []
        body = _normalise_terms(query)
        if not body:
            return []
        sql = text(
            """
            SELECT doc_id,
                   ts_rank_cd(tsv, plainto_tsquery('english', :query)) AS score
            FROM kb_lexical_index
            WHERE workspace_id = :ws
              AND tsv @@ plainto_tsquery('english', :query)
            ORDER BY score DESC, doc_id
            LIMIT :k
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, self._workspace_id)
            rows = (
                await conn.execute(
                    sql,
                    {"ws": self._workspace_id, "query": body, "k": k},
                )
            ).all()
        return [LexicalHit(doc_id=_coerce_uuid(row[0]), score=float(row[1])) for row in rows]

    async def delete(self, doc_id: UUID) -> bool:
        sql = text(
            """
            DELETE FROM kb_lexical_index
            WHERE workspace_id = :ws AND doc_id = :doc_id
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, self._workspace_id)
            result = await conn.execute(
                sql,
                {"ws": self._workspace_id, "doc_id": doc_id},
            )
        return bool(result.rowcount)


def _normalise_terms(terms: str | Iterable[str]) -> str:
    if isinstance(terms, str):
        return terms.strip()
    return " ".join(str(term).strip() for term in terms if str(term).strip())


def _coerce_uuid(value: object) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


__all__ = ["LexicalHit", "PostgresLexicalIndex"]
