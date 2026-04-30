"""Retrieval helpers: RRF fusion, tombstone tracking, content-hash diff.

These primitives compose with the existing ``InMemoryVectorStore`` and
BM25 path to deliver hybrid retrieval (S205) and re-ingest semantics
(S208 tombstones + S209 hash-diff) without imposing a particular
storage backend.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from uuid import UUID

from loop_kb_engine.models import Chunk

__all__ = [
    "ChunkDiff",
    "TombstoneRegistry",
    "chunk_content_hash",
    "diff_chunks",
    "rrf_combine",
]


def rrf_combine(
    rankings: list[list[tuple[Chunk, float]]],
    *,
    k: int = 60,
    top_k: int | None = None,
) -> list[tuple[Chunk, float]]:
    """Reciprocal Rank Fusion.

    For each ranked list, contributes ``1 / (k + rank)`` (rank is 1-based)
    to a chunk's fused score. The score float carried alongside each
    chunk in the input rankings is *not* used — RRF is rank-based.

    Args:
        rankings: One ranked list per retriever, sorted best-first.
        k: RRF constant. Higher dampens tail contributions.
        top_k: Optional cap on returned results.

    Returns:
        Chunks sorted by fused score descending. Ties broken by chunk id
        for determinism.
    """

    if k <= 0:
        raise ValueError("k must be positive")
    fused: dict[UUID, tuple[Chunk, float]] = {}
    for ranking in rankings:
        for rank, (chunk, _score) in enumerate(ranking, start=1):
            contrib = 1.0 / (k + rank)
            existing = fused.get(chunk.id)
            if existing is None:
                fused[chunk.id] = (chunk, contrib)
            else:
                fused[chunk.id] = (existing[0], existing[1] + contrib)
    out = list(fused.values())
    out.sort(key=lambda pair: (-pair[1], str(pair[0].id)))
    if top_k is not None and top_k >= 0:
        out = out[:top_k]
    return out


# ---------------------------------------------------------------------------
# Tombstones (S208)
# ---------------------------------------------------------------------------


@dataclass
class TombstoneRegistry:
    """Workspace-scoped record of deleted documents.

    Chunks may be physically removed from the vector store, but the
    document id is retained here so audit trails (which chunk answered
    which turn) still resolve. Storage is in-memory; production wiring
    persists to ``kb_documents`` with a ``deleted_at`` column.
    """

    _entries: dict[UUID, set[UUID]] = field(default_factory=dict)

    def mark_deleted(self, *, workspace_id: UUID, document_id: UUID) -> None:
        self._entries.setdefault(workspace_id, set()).add(document_id)

    def is_deleted(self, *, workspace_id: UUID, document_id: UUID) -> bool:
        return document_id in self._entries.get(workspace_id, set())

    def list_deleted(self, *, workspace_id: UUID) -> tuple[UUID, ...]:
        return tuple(sorted(self._entries.get(workspace_id, set()), key=str))

    def filter_active(
        self,
        *,
        workspace_id: UUID,
        chunks: list[Chunk],
    ) -> list[Chunk]:
        deleted = self._entries.get(workspace_id, set())
        if not deleted:
            return list(chunks)
        return [c for c in chunks if c.document_id not in deleted]


# ---------------------------------------------------------------------------
# Content-hash diff for re-ingest (S209)
# ---------------------------------------------------------------------------


def chunk_content_hash(chunk: Chunk) -> str:
    """Stable sha256 over (text, sorted metadata).

    The chunk *id* is intentionally excluded so a re-parsed document
    that produces semantically identical chunks lines up against the
    previous ingest.
    """

    h = hashlib.sha256()
    h.update(chunk.text.encode("utf-8"))
    for key in sorted(chunk.metadata):
        h.update(b"\x00")
        h.update(key.encode("utf-8"))
        h.update(b"\x00")
        h.update(chunk.metadata[key].encode("utf-8"))
    return h.hexdigest()


@dataclass(frozen=True)
class ChunkDiff:
    """Result of comparing two chunk sets for the same document."""

    added: tuple[Chunk, ...]
    removed: tuple[Chunk, ...]
    unchanged: tuple[Chunk, ...]

    @property
    def is_noop(self) -> bool:
        return not self.added and not self.removed


def diff_chunks(
    *,
    previous: list[Chunk],
    current: list[Chunk],
) -> ChunkDiff:
    """Compute add/remove/unchanged sets keyed by content hash.

    The output preserves source order: ``added`` follows ``current``
    order, ``removed`` follows ``previous`` order, ``unchanged`` follows
    ``current`` order.
    """

    prev_by_hash: dict[str, Chunk] = {chunk_content_hash(c): c for c in previous}
    curr_by_hash: dict[str, Chunk] = {chunk_content_hash(c): c for c in current}

    added = tuple(c for c in current if chunk_content_hash(c) not in prev_by_hash)
    removed = tuple(c for c in previous if chunk_content_hash(c) not in curr_by_hash)
    unchanged = tuple(c for c in current if chunk_content_hash(c) in prev_by_hash)
    return ChunkDiff(added=added, removed=removed, unchanged=unchanged)
