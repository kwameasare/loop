"""Episodic retrieval at turn-start (S492).

When a new turn begins, we want to surface relevant prior episodes
*plus* recent ones to the prompt: pure semantic similarity drops the
"two minutes ago we picked plan X" fact, pure recency drops the
"three days ago they said they hate phone calls" fact. We blend.

The retriever takes a vector index abstraction (any
``EpisodicReader``) so the same blending math runs against Qdrant in
production and a list-of-entries in tests.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from loop_kb_engine.episodic import EPISODIC_PAYLOAD_KEYS

DEFAULT_K = 5
DEFAULT_RECENCY_WEIGHT = 0.3
DEFAULT_SIMILARITY_WEIGHT = 0.7
DEFAULT_HALF_LIFE_MS = 1000 * 60 * 60 * 24 * 3  # 3 days


class RetrievalError(ValueError):
    """Retrieval policy / index call rejected."""


@dataclass(frozen=True, slots=True)
class EpisodicCandidate:
    """One stored episode with its vector similarity score."""

    point_id: str
    similarity: float  # cosine in [-1, 1]; treated as [0, 1] after normalisation
    occurred_at_ms: int
    payload: dict[str, object]


@runtime_checkable
class EpisodicReader(Protocol):
    """Qdrant-shaped read surface (mocked in tests)."""

    async def search(
        self,
        *,
        agent_id: str,
        query_vector: Sequence[float],
        limit: int,
    ) -> list[EpisodicCandidate]: ...


@dataclass(frozen=True, slots=True)
class RetrievalPolicy:
    """How to blend recency + similarity."""

    k: int = DEFAULT_K
    recency_weight: float = DEFAULT_RECENCY_WEIGHT
    similarity_weight: float = DEFAULT_SIMILARITY_WEIGHT
    half_life_ms: int = DEFAULT_HALF_LIFE_MS
    max_age_ms: int | None = None  # filter candidates older than this

    def __post_init__(self) -> None:
        if self.k < 1:
            raise RetrievalError("k must be >=1")
        if not (0.0 <= self.recency_weight <= 1.0):
            raise RetrievalError("recency_weight must be in [0,1]")
        if not (0.0 <= self.similarity_weight <= 1.0):
            raise RetrievalError("similarity_weight must be in [0,1]")
        total = self.recency_weight + self.similarity_weight
        if not math.isclose(total, 1.0, abs_tol=1e-6):
            raise RetrievalError(
                f"recency_weight + similarity_weight must sum to 1 (got {total})"
            )
        if self.half_life_ms < 1000:
            raise RetrievalError("half_life_ms must be >=1000")


@dataclass(frozen=True, slots=True)
class ScoredEpisode:
    candidate: EpisodicCandidate
    similarity_norm: float
    recency_norm: float
    score: float


def recency_score(*, occurred_at_ms: int, now_ms: int, half_life_ms: int) -> float:
    """Exponential decay: 1.0 at now, 0.5 at one half-life ago."""
    age = max(0, now_ms - occurred_at_ms)
    return math.pow(0.5, age / half_life_ms)


def normalise_similarity(sim: float) -> float:
    """Map cosine similarity from [-1, 1] to [0, 1]."""
    return max(0.0, min(1.0, (sim + 1.0) / 2.0))


async def retrieve_for_turn(
    *,
    reader: EpisodicReader,
    agent_id: str,
    query_vector: Sequence[float],
    now_ms: int,
    policy: RetrievalPolicy,
    candidate_pool: int | None = None,
) -> list[ScoredEpisode]:
    """Return the top-K episodes blending recency + similarity."""
    if not query_vector:
        raise RetrievalError("query_vector must be non-empty")
    pool = candidate_pool if candidate_pool is not None else max(policy.k * 4, 16)
    candidates = await reader.search(
        agent_id=agent_id, query_vector=query_vector, limit=pool
    )
    scored: list[ScoredEpisode] = []
    for c in candidates:
        if policy.max_age_ms is not None and now_ms - c.occurred_at_ms > policy.max_age_ms:
            continue
        sim_norm = normalise_similarity(c.similarity)
        rec = recency_score(
            occurred_at_ms=c.occurred_at_ms,
            now_ms=now_ms,
            half_life_ms=policy.half_life_ms,
        )
        score = policy.similarity_weight * sim_norm + policy.recency_weight * rec
        scored.append(
            ScoredEpisode(
                candidate=c, similarity_norm=sim_norm, recency_norm=rec, score=score
            )
        )
    scored.sort(key=lambda s: s.score, reverse=True)
    return scored[: policy.k]


def validate_payload(payload: dict[str, object]) -> None:
    """Cheap pre-flight check used at write time + retrieval time."""
    missing = [k for k in EPISODIC_PAYLOAD_KEYS if k not in payload]
    if missing:
        raise RetrievalError(f"episodic payload missing required keys: {missing}")


__all__ = [
    "DEFAULT_HALF_LIFE_MS",
    "DEFAULT_K",
    "DEFAULT_RECENCY_WEIGHT",
    "DEFAULT_SIMILARITY_WEIGHT",
    "EpisodicCandidate",
    "EpisodicReader",
    "RetrievalError",
    "RetrievalPolicy",
    "ScoredEpisode",
    "normalise_similarity",
    "recency_score",
    "retrieve_for_turn",
    "validate_payload",
]
