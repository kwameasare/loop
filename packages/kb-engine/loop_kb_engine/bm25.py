"""BM25 Okapi sparse search (S204).

Pure-Python implementation of BM25 (k1=1.2, b=0.75 by default), with
per-(workspace, agent) index isolation matching ADR-002. The
production Postgres path uses ``tsvector`` with the same scoring
weights so results stay comparable across backends.

Tokenisation is intentionally minimalist: lowercase, split on
non-alphanumeric. KB ingestion can pre-tokenise with a richer
analyser and pass token lists directly.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

__all__ = ["BM25Hit", "BM25Index", "tokenise"]


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def tokenise(text: str) -> list[str]:
    """Lowercase + alphanumeric split. Stable across CPython versions."""
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]


@dataclass(frozen=True)
class BM25Hit:
    chunk_id: str
    score: float
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass
class _IndexShard:
    df: Counter[str] = field(default_factory=Counter)
    docs: dict[str, tuple[Counter[str], int, Mapping[str, str]]] = field(
        default_factory=dict
    )
    total_length: int = 0


class BM25Index:
    """In-memory BM25 with per-(workspace, agent) shards.

    ``upsert`` is idempotent on ``chunk_id`` — re-indexing a chunk
    swaps the document-frequency contributions cleanly.
    """

    def __init__(self, *, k1: float = 1.2, b: float = 0.75) -> None:
        if k1 <= 0:
            raise ValueError("k1 must be positive")
        if not 0 <= b <= 1:
            raise ValueError("b must be in [0,1]")
        self._k1 = k1
        self._b = b
        self._shards: dict[tuple[str, str], _IndexShard] = {}

    def upsert(
        self,
        *,
        workspace_id: str,
        agent_id: str,
        chunk_id: str,
        text: str,
        metadata: Mapping[str, str] | None = None,
    ) -> None:
        shard = self._shards.setdefault((workspace_id, agent_id), _IndexShard())
        # If the chunk already exists, withdraw its DF contributions first.
        if chunk_id in shard.docs:
            old_tf, old_len, _ = shard.docs[chunk_id]
            for term in old_tf:
                shard.df[term] -= 1
                if shard.df[term] <= 0:
                    del shard.df[term]
            shard.total_length -= old_len
        tokens = tokenise(text)
        tf = Counter(tokens)
        for term in tf:
            shard.df[term] += 1
        shard.docs[chunk_id] = (tf, len(tokens), dict(metadata or {}))
        shard.total_length += len(tokens)

    def remove(
        self, *, workspace_id: str, agent_id: str, chunk_id: str
    ) -> None:
        shard = self._shards.get((workspace_id, agent_id))
        if shard is None or chunk_id not in shard.docs:
            return
        tf, length, _ = shard.docs.pop(chunk_id)
        for term in tf:
            shard.df[term] -= 1
            if shard.df[term] <= 0:
                del shard.df[term]
        shard.total_length -= length

    def search(
        self,
        *,
        workspace_id: str,
        agent_id: str,
        query: str,
        top_k: int = 10,
        score_threshold: float | None = None,
    ) -> list[BM25Hit]:
        shard = self._shards.get((workspace_id, agent_id))
        if shard is None or not shard.docs:
            return []
        q_terms = tokenise(query)
        if not q_terms:
            return []
        n_docs = len(shard.docs)
        avgdl = shard.total_length / n_docs if n_docs else 0.0
        idf: dict[str, float] = {}
        for term in set(q_terms):
            df = shard.df.get(term, 0)
            # BM25+ idf (Robertson-Spärck-Jones with Lucene smoothing).
            idf[term] = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
        hits: list[BM25Hit] = []
        for chunk_id, (tf, doc_len, meta) in shard.docs.items():
            score = 0.0
            for term in q_terms:
                f = tf.get(term, 0)
                if f == 0:
                    continue
                norm = 1 - self._b + self._b * (doc_len / avgdl) if avgdl else 1.0
                score += idf[term] * (f * (self._k1 + 1)) / (
                    f + self._k1 * norm
                )
            if score <= 0:
                continue
            if score_threshold is not None and score < score_threshold:
                continue
            hits.append(BM25Hit(chunk_id=chunk_id, score=score, metadata=meta))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]

    def shards(self) -> Iterable[tuple[str, str]]:
        return tuple(self._shards.keys())
