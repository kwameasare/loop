"""Zep EpisodicStore adapter (S821)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, cast, runtime_checkable
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
    md_raw = record.get("metadata")
    if not isinstance(md_raw, dict):
        raise ZepError("record missing metadata")
    md = cast("dict[str, object]", md_raw)
    summary = record.get("summary")
    if not isinstance(summary, str) or not summary:
        raise ZepError(f"record missing 'summary' string: {record!r}")
    embedding = record.get("embedding")
    if not isinstance(embedding, (list, tuple)):
        raise ZepError("record missing embedding")
    parsed_values: list[float] = []
    for value in cast("Sequence[object]", embedding):
        if not isinstance(value, (int, float, str)):
            raise ZepError("embedding contains non-numeric value")
        parsed_values.append(float(value))
    values = tuple(parsed_values)
    if len(values) != EMBEDDING_DIM:
        raise ZepError(f"embedding dim {len(values)} != {EMBEDDING_DIM}")
    try:
        salience = md["salience"]
        ts_ms = md["ts_ms"]
        if not isinstance(salience, (int, float, str)):
            raise ZepError("metadata salience must be numeric")
        if not isinstance(ts_ms, (int, float, str)):
            raise ZepError("metadata ts_ms must be numeric")
        return EpisodicEntry(
            id=UUID(str(md["loop_id"])),
            workspace_id=UUID(str(md["workspace_id"])),
            agent_id=UUID(str(md["agent_id"])),
            conversation_id=UUID(str(md["conversation_id"])),
            summary=summary,
            embedding=values,
            salience=float(salience),
            ts_ms=int(ts_ms),
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
    ) -> list[tuple[EpisodicEntry, float]]:
        if limit <= 0:
            raise ZepError("limit must be positive")
        try:
            records = await self.client.search(
                session_id=_session_id(workspace_id, agent_id),
                embedding=embedding,
                limit=max(limit * 2, limit),
            )
            scored: list[tuple[EpisodicEntry, float]] = []
            for record in records:
                entry = _entry(record)
                raw_score = record.get("score")
                score = raw_score if isinstance(raw_score, (int, float)) else cosine_similarity(
                    tuple(float(x) for x in embedding),
                    entry.embedding,
                )
                if float(score) >= min_score:
                    scored.append((entry, float(score)))
        except ZepError:
            raise
        except Exception as exc:
            raise ZepError(f"failed to query Zep episodes: {exc}") from exc
        scored.sort(key=lambda item: (-item[1], -item[0].salience, item[0].ts_ms))
        return scored[:limit]

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
