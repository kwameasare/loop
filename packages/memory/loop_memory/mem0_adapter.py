"""Mem0 EpisodicStore adapter (S820).

Mem0 (https://mem0.ai) is a popular drop-in long-term-memory store
for agents. We wrap it behind Loop's ``EpisodicStore`` Protocol so
existing runtime code keeps working unchanged when a workspace opts
into Mem0.

The Mem0 SDK is hidden behind a tiny ``Mem0Client`` Protocol so the
adapter is unit-testable without a network or a Mem0 account. The
production wiring lives in the data-plane bootstrap, not here.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from loop_memory.episodic import (
    EMBEDDING_DIM,
    EpisodicEntry,
    EpisodicError,
    cosine_similarity,
)


class Mem0Error(EpisodicError):
    """Mem0 API call failed or returned malformed data."""


@runtime_checkable
class Mem0Client(Protocol):
    """The slice of mem0 we depend on."""

    async def add(
        self,
        *,
        user_id: str,
        memory: str,
        metadata: dict[str, Any],
        embedding: Sequence[float],
    ) -> str: ...

    async def search(
        self,
        *,
        user_id: str,
        embedding: Sequence[float],
        limit: int,
    ) -> list[dict[str, Any]]: ...

    async def list(
        self,
        *,
        user_id: str,
        limit: int,
    ) -> list[dict[str, Any]]: ...


def _user_id(workspace_id: UUID, agent_id: UUID) -> str:
    """Mem0 keys memories on a single ``user_id``; we synthesise one."""
    return f"loop:{workspace_id.hex}:{agent_id.hex}"


def _to_metadata(entry: EpisodicEntry) -> dict[str, Any]:
    return {
        "loop_id": str(entry.id),
        "workspace_id": str(entry.workspace_id),
        "agent_id": str(entry.agent_id),
        "conversation_id": str(entry.conversation_id),
        "salience": entry.salience,
        "ts_ms": entry.ts_ms,
    }


def _from_record(record: dict[str, Any]) -> EpisodicEntry:
    """Rehydrate an EpisodicEntry from a mem0 record."""
    md = record.get("metadata") or {}
    summary = record.get("memory")
    if not isinstance(summary, str) or not summary:
        raise Mem0Error(f"record missing 'memory' string: {record!r}")
    embedding = record.get("embedding")
    if not isinstance(embedding, (list, tuple)):
        raise Mem0Error("record missing embedding")
    if len(embedding) != EMBEDDING_DIM:
        raise Mem0Error(
            f"embedding dim {len(embedding)} != {EMBEDDING_DIM}"
        )
    try:
        return EpisodicEntry(
            id=UUID(md["loop_id"]),
            workspace_id=UUID(md["workspace_id"]),
            agent_id=UUID(md["agent_id"]),
            conversation_id=UUID(md["conversation_id"]),
            summary=summary,
            embedding=tuple(float(x) for x in embedding),
            salience=float(md["salience"]),
            ts_ms=int(md["ts_ms"]),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise Mem0Error(f"failed to rehydrate record: {exc}") from exc


@dataclass(slots=True)
class Mem0EpisodicStore:
    """``EpisodicStore`` Protocol implementation backed by Mem0."""

    client: Mem0Client

    async def upsert(self, entry: EpisodicEntry) -> None:
        try:
            await self.client.add(
                user_id=_user_id(entry.workspace_id, entry.agent_id),
                memory=entry.summary,
                metadata=_to_metadata(entry),
                embedding=entry.embedding,
            )
        except Mem0Error:
            raise
        except Exception as exc:
            raise Mem0Error(f"mem0.add failed: {exc}") from exc

    async def query(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        embedding: Sequence[float],
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[tuple[EpisodicEntry, float]]:
        if limit <= 0:
            raise Mem0Error("limit must be positive")
        try:
            records = await self.client.search(
                user_id=_user_id(workspace_id, agent_id),
                embedding=embedding,
                limit=max(limit * 2, limit),
            )
        except Exception as exc:
            raise Mem0Error(f"mem0.search failed: {exc}") from exc
        scored: list[tuple[EpisodicEntry, float]] = []
        for rec in records:
            entry = _from_record(rec)
            score_raw = rec.get("score")
            score = (
                float(score_raw)
                if isinstance(score_raw, (int, float))
                else cosine_similarity(entry.embedding, embedding)
            )
            if score < min_score:
                continue
            scored.append((entry, score))
        scored.sort(key=lambda pair: (-pair[1], -pair[0].salience, pair[0].ts_ms))
        return scored[:limit]

    async def list_recent(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        limit: int = 20,
    ) -> list[EpisodicEntry]:
        if limit <= 0:
            raise Mem0Error("limit must be positive")
        try:
            records = await self.client.list(
                user_id=_user_id(workspace_id, agent_id), limit=limit
            )
        except Exception as exc:
            raise Mem0Error(f"mem0.list failed: {exc}") from exc
        entries = [_from_record(r) for r in records]
        entries.sort(key=lambda e: e.ts_ms, reverse=True)
        return entries[:limit]


__all__ = [
    "Mem0Client",
    "Mem0EpisodicStore",
    "Mem0Error",
]
