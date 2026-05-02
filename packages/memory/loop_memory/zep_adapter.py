"""Zep EpisodicStore adapter (S821)."""

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


class ZepError(EpisodicError):
    """Zep API call failed or returned malformed data."""


@runtime_checkable
class ZepClient(Protocol):
    """The small async Zep surface needed by Loop."""

    async def add_episode(
        self,
        *,
        session_id: str,
        summary: str,
        metadata: dict[str, Any],
        embedding: Sequence[float],
    ) -> str: ...

    async def search(
        self,
        *,
        session_id: str,
        embedding: Sequence[float],
        limit: int,
    ) -> list[dict[str, Any]]: ...

    async def list_episodes(
        self,
        *,
        session_id: str,
        limit: int,
    ) -> list[dict[str, Any]]: ...


def _session_id(workspace_id: UUID, agent_id: UUID) -> str:
    return f"loop:{workspace_id.hex}:{agent_id.hex}"


def _metadata(entry: EpisodicEntry) -> dict[str, Any]:
    return {
        "loop_id": str(entry.id),
        "workspace_id": str(entry.workspace_id),
        "agent_id": str(entry.agent_id),
        "conversation_id": str(entry.conversation_id),
        "salience": entry.salience,
        "ts_ms": entry.ts_ms,
    }


def _entry(record: dict[str, Any]) -> EpisodicEntry:
    md = record.get("metadata") or {}
    summary = record.get("summary")
    if not isinstance(summary, str) or not summary:
        raise ZepError(f"record missing 'summary' string: {record!r}")
    embedding = record.get("embedding")
    if not isinstance(embedding, (list, tuple)):
        raise ZepError("record missing embedding")
    if len(embedding) != EMBEDDING_DIM:
        raise ZepError(f"embedding dim {len(embedding)} != {EMBEDDING_DIM}")
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
    except (KeyError, TypeError, ValueError) as exc:
        raise ZepError(f"failed to rehydrate record: {exc}") from exc


@dataclass(slots=True)
class ZepEpisodicStore:
    """EpisodicStore backed by a Zep-compatible async client."""

    client: ZepClient

    async def upsert(self, entry: EpisodicEntry) -> None:
        try:
            await self.client.add_episode(
                session_id=_session_id(entry.workspace_id, entry.agent_id),
                summary=entry.summary,
                metadata=_metadata(entry),
                embedding=entry.embedding,
            )
        except Exception as exc:
            raise ZepError(f"failed to upsert Zep episode: {exc}") from exc

    async def query(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        embedding: Sequence[float],
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[EpisodicEntry]:
        if limit <= 0:
            raise ZepError("limit must be positive")
        try:
            records = await self.client.search(
                session_id=_session_id(workspace_id, agent_id),
                embedding=embedding,
                limit=max(limit * 2, limit),
            )
            scored = []
            for record in records:
                entry = _entry(record)
                raw_score = record.get("score")
                score = raw_score if isinstance(raw_score, (int, float)) else cosine_similarity(
                    tuple(float(x) for x in embedding),
                    entry.embedding,
                )
                if float(score) >= min_score:
                    scored.append((float(score), entry))
        except ZepError:
            raise
        except Exception as exc:
            raise ZepError(f"failed to query Zep episodes: {exc}") from exc
        scored.sort(key=lambda item: (-item[0], -item[1].salience, item[1].ts_ms))
        return [entry for _, entry in scored[:limit]]

    async def list_recent(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        limit: int = 20,
    ) -> list[EpisodicEntry]:
        if limit <= 0:
            raise ZepError("limit must be positive")
        try:
            records = await self.client.list_episodes(
                session_id=_session_id(workspace_id, agent_id),
                limit=limit,
            )
            entries = [_entry(record) for record in records]
        except ZepError:
            raise
        except Exception as exc:
            raise ZepError(f"failed to list Zep episodes: {exc}") from exc
        return sorted(entries, key=lambda entry: entry.ts_ms, reverse=True)[:limit]


__all__ = ["ZepClient", "ZepEpisodicStore", "ZepError"]
