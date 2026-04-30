"""Episodic memory tier (S035).

Long-form recall of past conversation slices. Each entry is a short
summary plus a vector embedding so the runtime can pull semantically
similar past episodes back into context.

This module ships the **Protocol contract** plus deterministic
in-memory implementations:

* :class:`EpisodicEntry` -- frozen pydantic record.
* :class:`Embedder` -- ``embed(text) -> tuple[float, ...]``.
* :class:`HashEmbedder` -- deterministic 16-dim embedder for tests.
* :class:`EpisodicStore` -- ``upsert`` / ``query`` / ``list_recent``.
* :class:`InMemoryEpisodicStore` -- cosine-similarity backed.
* :func:`auto_summarize` -- deterministic message-list summariser.

The Qdrant + LLM-summariser production adapters are deferred to
S035b; the Protocol is what the runtime depends on.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

EMBEDDING_DIM = 16


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class EpisodicEntry(_StrictModel):
    """One past conversation slice, summarised + embedded."""

    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    agent_id: UUID
    conversation_id: UUID
    summary: str = Field(min_length=1)
    embedding: tuple[float, ...] = Field(min_length=EMBEDDING_DIM, max_length=EMBEDDING_DIM)
    salience: float = Field(ge=0.0, le=1.0)
    ts_ms: int = Field(ge=0)


class EpisodicError(RuntimeError):
    """Raised on invalid episodic-memory operations."""


@runtime_checkable
class Embedder(Protocol):
    """Maps a text string to a fixed-size vector."""

    def embed(self, text: str) -> tuple[float, ...]: ...


class HashEmbedder:
    """Deterministic SHA-256 based embedder.

    Splits the SHA-256 digest into ``EMBEDDING_DIM`` little-endian
    16-bit words, normalises to unit length, and returns the tuple.
    Identical inputs always yield identical embeddings; different
    inputs are essentially uniform on the unit sphere. Useful for
    tests and offline development; production swaps in a real
    embedding model.
    """

    def embed(self, text: str) -> tuple[float, ...]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # 32 bytes -> 16 x uint16 -> centred + normalised.
        raw = [int.from_bytes(digest[i : i + 2], "little") for i in range(0, 32, 2)]
        # Centre around zero so cosine similarity is meaningful.
        centred = [v - 32_768 for v in raw]
        norm = math.sqrt(sum(x * x for x in centred))
        if norm == 0:
            return (0.0,) * EMBEDDING_DIM
        return tuple(x / norm for x in centred)


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise EpisodicError(f"vector length mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


@runtime_checkable
class EpisodicStore(Protocol):
    """Persistent recall of past episodes, scoped per agent."""

    async def upsert(self, entry: EpisodicEntry) -> None: ...

    async def query(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        embedding: Sequence[float],
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[tuple[EpisodicEntry, float]]: ...

    async def list_recent(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        limit: int = 20,
    ) -> list[EpisodicEntry]: ...


@dataclass
class InMemoryEpisodicStore:
    """Test/dev episodic store backed by a dict and brute-force cosine."""

    _entries: dict[UUID, EpisodicEntry] = field(default_factory=dict)

    async def upsert(self, entry: EpisodicEntry) -> None:
        self._entries[entry.id] = entry

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
            raise EpisodicError("limit must be positive")
        scored: list[tuple[EpisodicEntry, float]] = []
        for entry in self._entries.values():
            if entry.workspace_id != workspace_id or entry.agent_id != agent_id:
                continue
            score = cosine_similarity(entry.embedding, embedding)
            if score < min_score:
                continue
            scored.append((entry, score))
        # Sort by score desc, then salience desc for stable ranking.
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
            raise EpisodicError("limit must be positive")
        scoped = [
            e
            for e in self._entries.values()
            if e.workspace_id == workspace_id and e.agent_id == agent_id
        ]
        scoped.sort(key=lambda e: e.ts_ms, reverse=True)
        return scoped[:limit]


def auto_summarize(messages: Iterable[str], *, max_chars: int = 240) -> str:
    """Deterministic summariser for episodic memory.

    Joins messages with " | ", trims to ``max_chars``, and appends
    an ellipsis if it had to truncate. Real adapter swaps in an LLM
    summariser; this keeps the contract testable.
    """

    if max_chars <= 0:
        raise EpisodicError("max_chars must be positive")
    joined = " | ".join(m.strip() for m in messages if m.strip())
    if not joined:
        raise EpisodicError("auto_summarize requires at least one non-empty message")
    if len(joined) <= max_chars:
        return joined
    return joined[: max_chars - 1].rstrip() + "\u2026"


__all__ = [
    "EMBEDDING_DIM",
    "Embedder",
    "EpisodicEntry",
    "EpisodicError",
    "EpisodicStore",
    "HashEmbedder",
    "InMemoryEpisodicStore",
    "auto_summarize",
    "cosine_similarity",
]
