"""Zep EpisodicStore adapter (S821)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from loop_memory.episodic import (
    EMBEDDING_DIM,
    EpisodicEntry,
    EpisodicError,
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


__all__ = ["ZepClient", "ZepError"]
