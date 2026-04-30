"""Vector store abstraction + in-memory impl.

ADR-002 selects Qdrant as the production vector store; the real
adapter lands with S015b once the qdrant-client dependency is wired
up. The Protocol below is what KnowledgeBase consumes, so swapping
the impl is a one-line change.
"""

from __future__ import annotations

import asyncio
import math
from typing import Protocol, runtime_checkable
from uuid import UUID

from loop_kb_engine.models import Chunk


@runtime_checkable
class VectorStore(Protocol):
    """Tenant-isolated dense-vector index."""

    async def upsert(
        self,
        *,
        workspace_id: UUID,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None: ...

    async def query(
        self,
        *,
        workspace_id: UUID,
        embedding: list[float],
        top_k: int,
    ) -> list[tuple[Chunk, float]]: ...

    async def delete_document(self, *, workspace_id: UUID, document_id: UUID) -> int: ...


class InMemoryVectorStore:
    """Cosine-similarity in-memory store. Vectors are kept normalised
    by the embedder, so cosine reduces to a dot product."""

    def __init__(self) -> None:
        self._rows: dict[UUID, list[tuple[Chunk, list[float]]]] = {}
        self._lock = asyncio.Lock()

    async def upsert(
        self,
        *,
        workspace_id: UUID,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must align")
        async with self._lock:
            bucket = self._rows.setdefault(workspace_id, [])
            existing_ids = {c.id for c, _ in bucket}
            for chunk, emb in zip(chunks, embeddings, strict=True):
                if chunk.workspace_id != workspace_id:
                    raise ValueError("chunk.workspace_id != workspace_id")
                if chunk.id in existing_ids:
                    bucket[:] = [(c, e) for c, e in bucket if c.id != chunk.id]
                bucket.append((chunk, list(emb)))

    async def query(
        self,
        *,
        workspace_id: UUID,
        embedding: list[float],
        top_k: int,
    ) -> list[tuple[Chunk, float]]:
        if top_k <= 0:
            return []
        async with self._lock:
            bucket = list(self._rows.get(workspace_id, []))
        scored = [(chunk, _cosine(embedding, emb)) for chunk, emb in bucket]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]

    async def delete_document(self, *, workspace_id: UUID, document_id: UUID) -> int:
        async with self._lock:
            bucket = self._rows.get(workspace_id, [])
            keep = [(c, e) for c, e in bucket if c.document_id != document_id]
            removed = len(bucket) - len(keep)
            self._rows[workspace_id] = keep
            return removed


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


__all__ = ["InMemoryVectorStore", "VectorStore"]
