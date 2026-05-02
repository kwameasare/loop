"""Synthetic 1M-chunk retrieval fixture for performance gates."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from loop_kb_engine.bm25 import tokenise

DEFAULT_CHUNK_COUNT = 1_000_000
DEFAULT_TOP_K = 8
TARGET_P50_MS = 200.0


@dataclass(frozen=True, slots=True)
class SyntheticKBHit:
    chunk_id: str
    score: float
    matched_terms: tuple[str, ...]


class SyntheticMillionChunkFixture:
    """Virtual KB corpus with deterministic sparse postings.

    The fixture intentionally avoids allocating a million chunk objects.
    It models a 1M-chunk inverted index by deriving compact postings lists
    for query terms from stable hashes, then ranks the union of postings.
    """

    def __init__(
        self, *, chunk_count: int = DEFAULT_CHUNK_COUNT, postings_per_term: int = 64
    ) -> None:
        if chunk_count < 1:
            raise ValueError("chunk_count must be > 0")
        if postings_per_term < 1:
            raise ValueError("postings_per_term must be > 0")
        self.chunk_count = chunk_count
        self.postings_per_term = postings_per_term

    def search(self, query: str, *, top_k: int = DEFAULT_TOP_K) -> list[SyntheticKBHit]:
        if top_k < 1:
            raise ValueError("top_k must be >= 1")
        terms = tuple(dict.fromkeys(tokenise(query)))
        if not terms:
            return []

        scores: dict[int, float] = {}
        matches: dict[int, set[str]] = {}
        for term_index, term in enumerate(terms):
            for rank, doc_id in enumerate(self._postings(term), start=1):
                scores[doc_id] = scores.get(doc_id, 0.0) + self._score(term_index, rank)
                matches.setdefault(doc_id, set()).add(term)

        ranked = sorted(scores, key=lambda doc_id: (-scores[doc_id], doc_id))[:top_k]
        return [
            SyntheticKBHit(
                chunk_id=f"chunk-{doc_id:07d}",
                score=round(scores[doc_id], 6),
                matched_terms=tuple(sorted(matches[doc_id])),
            )
            for doc_id in ranked
        ]

    def _postings(self, term: str) -> tuple[int, ...]:
        seed = int.from_bytes(
            hashlib.blake2b(term.encode("utf-8"), digest_size=8).digest(),
            "big",
        )
        step = (seed % 997) + 1
        start = seed % self.chunk_count
        return tuple((start + i * step) % self.chunk_count for i in range(self.postings_per_term))

    def _score(self, term_index: int, rank: int) -> float:
        term_boost = 1.0 / (term_index + 1)
        return term_boost / (rank + 1)


__all__ = [
    "DEFAULT_CHUNK_COUNT",
    "DEFAULT_TOP_K",
    "TARGET_P50_MS",
    "SyntheticKBHit",
    "SyntheticMillionChunkFixture",
]
