"""ColBERT-style late-interaction retrieval (S826).

Late interaction computes relevance as the sum of maximum cosine similarities
between every query token vector and all document token vectors (MaxSim).
This is the core idea from ColBERT:

    score(q, d) = Σ_{i=1}^{|q|} max_{j=1}^{|d|} sim(q_i, d_j)

This module provides:

* ``TokenEmbedding`` — a per-token vector tied to a Chunk.
* ``LateInteractionIndex`` — stores document token embeddings keyed by
  chunk id and computes MaxSim scores.
* ``late_interaction_retrieve`` — top-level opt-in retrieval function that
  returns chunks ranked by MaxSim score.

The module is intentionally storage-backend-agnostic: embeddings are stored
in memory as plain Python dicts.  A production deployment would persist
``TokenEmbedding`` rows in Postgres or Qdrant multi-vector support.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from uuid import UUID

from loop_kb_engine.models import Chunk

__all__ = [
    "TokenEmbedding",
    "LateInteractionIndex",
    "late_interaction_retrieve",
    "maxsim",
]


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TokenEmbedding:
    """Dense vector for a single token inside a chunk.

    ``ordinal`` is the position of the token within the chunk's token
    sequence (0-based).  ``values`` is a unit-normalised float tuple.
    """

    chunk_id: UUID
    ordinal: int
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.values:
            raise ValueError("values must be non-empty")
        if self.ordinal < 0:
            raise ValueError("ordinal must be >= 0")


# ---------------------------------------------------------------------------
# MaxSim primitive
# ---------------------------------------------------------------------------


def _dot(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Dot product of two equal-length tuples."""
    if len(a) != len(b):
        raise ValueError(f"dimension mismatch: {len(a)} vs {len(b)}")
    return sum(x * y for x, y in zip(a, b))


def _norm(v: tuple[float, ...]) -> float:
    return math.sqrt(sum(x * x for x in v))


def cosine_sim(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Cosine similarity between two vectors.  Returns 0 if either is zero."""
    na, nb = _norm(a), _norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return _dot(a, b) / (na * nb)


def maxsim(
    query_tokens: list[tuple[float, ...]],
    doc_tokens: list[tuple[float, ...]],
) -> float:
    """MaxSim score between a query and a document (ColBERT formula).

    For each query token vector, finds the maximum cosine similarity
    among all document token vectors, then sums those maxima.

    Args:
        query_tokens: Ordered list of query token embedding vectors.
        doc_tokens: Ordered list of document token embedding vectors.

    Returns:
        MaxSim score (higher is more relevant).  Returns 0.0 if either
        list is empty.
    """
    if not query_tokens or not doc_tokens:
        return 0.0
    total = 0.0
    for q_vec in query_tokens:
        best = max(cosine_sim(q_vec, d_vec) for d_vec in doc_tokens)
        total += best
    return total


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------


class LateInteractionIndex:
    """In-memory index of per-token embeddings for late-interaction retrieval.

    Usage::

        idx = LateInteractionIndex()
        idx.add_chunk(chunk, token_embeddings)
        results = idx.query(query_token_vecs, top_k=10)
    """

    def __init__(self) -> None:
        # chunk_id → (Chunk, [token_vecs])
        self._store: dict[UUID, tuple[Chunk, list[tuple[float, ...]]]] = {}

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def add_chunk(
        self,
        chunk: Chunk,
        token_embeddings: list[TokenEmbedding],
    ) -> None:
        """Index a chunk together with its per-token embeddings.

        The ``TokenEmbedding`` list is sorted by ordinal before storage so
        callers may add tokens in arbitrary order.
        """
        sorted_toks = sorted(token_embeddings, key=lambda t: t.ordinal)
        doc_vecs = [te.values for te in sorted_toks]
        self._store[chunk.id] = (chunk, doc_vecs)

    def remove_chunk(self, chunk_id: UUID) -> None:
        """Remove a chunk from the index (e.g. on GDPR erasure)."""
        self._store.pop(chunk_id, None)

    @property
    def size(self) -> int:
        """Number of indexed chunks."""
        return len(self._store)

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def query(
        self,
        query_token_vecs: list[tuple[float, ...]],
        *,
        top_k: int = 10,
    ) -> list[tuple[Chunk, float]]:
        """Rank all indexed chunks by MaxSim score.

        Args:
            query_token_vecs: Per-token query embeddings (unit-normalised).
            top_k: Maximum number of results to return.

        Returns:
            List of (Chunk, score) sorted descending by MaxSim score.
        """
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        scored: list[tuple[Chunk, float]] = []
        for chunk, doc_vecs in self._store.values():
            score = maxsim(query_token_vecs, doc_vecs)
            scored.append((chunk, score))
        scored.sort(key=lambda pair: (-pair[1], str(pair[0].id)))
        return scored[:top_k]


# ---------------------------------------------------------------------------
# Convenience retrieval function
# ---------------------------------------------------------------------------


def late_interaction_retrieve(
    index: LateInteractionIndex,
    query_token_vecs: list[tuple[float, ...]],
    *,
    top_k: int = 10,
) -> list[tuple[Chunk, float]]:
    """Opt-in late-interaction (ColBERT-style) retrieval.

    A thin wrapper around ``LateInteractionIndex.query`` provided so callers
    can switch between retrieval modes with a single keyword argument::

        if mode == "late_interaction":
            results = late_interaction_retrieve(li_index, q_vecs, top_k=10)
        else:
            results = dense_retrieve(dense_index, q_vec, top_k=10)

    Returns:
        Top-k (Chunk, MaxSim score) pairs, sorted descending.
    """
    return index.query(query_token_vecs, top_k=top_k)
