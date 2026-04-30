"""KnowledgeBase: ingest -> chunk -> embed -> upsert; retrieve via
hybrid (BM25 lexical + dense vector) scoring.

The hybrid score is ``alpha * bm25 + (1 - alpha) * dense``, both
normalised to [0, 1] across the candidate set so the alpha knob has
predictable behaviour across heterogeneous corpora.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from loop_kb_engine.chunker import Chunker, SemanticChunker
from loop_kb_engine.embeddings import EmbeddingService
from loop_kb_engine.models import Chunk, Document
from loop_kb_engine.store import VectorStore

_TOKEN = re.compile(r"[A-Za-z0-9]+")


class RetrievalResult(BaseModel):
    """One retrieved chunk + the components of its hybrid score."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    chunk: Chunk
    score: float = Field(ge=0.0)
    bm25_score: float = Field(ge=0.0)
    dense_score: float = Field(ge=0.0, le=1.0)


class KnowledgeBase:
    def __init__(
        self,
        *,
        chunker: Chunker | None = None,
        embedder: EmbeddingService,
        vector_store: VectorStore,
    ) -> None:
        self._chunker: Chunker = chunker or SemanticChunker()
        self._embedder = embedder
        self._store = vector_store
        # Per-workspace lexical index for BM25 -- a tiny, dependency-free
        # implementation that fits the v0 scope. Real corpora swap in
        # Tantivy/OpenSearch later.
        self._lex: dict[UUID, dict[UUID, Chunk]] = {}

    # --------------------------------------------------------------- ingest

    async def ingest(self, document: Document) -> list[Chunk]:
        chunks = self._chunker.chunk(document)
        if not chunks:
            return []
        vectors = await self._embedder.embed([c.text for c in chunks])
        await self._store.upsert(
            workspace_id=document.workspace_id,
            chunks=chunks,
            embeddings=vectors,
        )
        bucket = self._lex.setdefault(document.workspace_id, {})
        for c in chunks:
            bucket[c.id] = c
        return chunks

    async def delete_document(self, *, workspace_id: UUID, document_id: UUID) -> int:
        removed = await self._store.delete_document(
            workspace_id=workspace_id, document_id=document_id
        )
        bucket = self._lex.get(workspace_id, {})
        bucket_keys = [k for k, c in bucket.items() if c.document_id == document_id]
        for k in bucket_keys:
            del bucket[k]
        return removed

    async def list_documents(self, *, workspace_id: UUID) -> tuple[UUID, ...]:
        """Return the distinct document_ids currently indexed for the workspace.

        Backs the cp-api ``GET /v1/kb/{workspace}/documents`` endpoint
        (S207) without leaking chunk-level state.
        """

        bucket = self._lex.get(workspace_id, {})
        return tuple(sorted({c.document_id for c in bucket.values()}, key=str))

    # ------------------------------------------------------------ retrieval

    async def retrieve(
        self,
        *,
        workspace_id: UUID,
        query: str,
        top_k: int = 5,
        alpha: float = 0.5,
    ) -> list[RetrievalResult]:
        if not 0.0 <= alpha <= 1.0:
            raise ValueError("alpha must be in [0, 1]")
        if top_k <= 0:
            return []

        candidate_k = max(top_k * 4, 20)

        # Dense leg
        query_emb = (await self._embedder.embed([query]))[0]
        dense_hits = await self._store.query(
            workspace_id=workspace_id, embedding=query_emb, top_k=candidate_k
        )
        dense_scores: dict[UUID, tuple[Chunk, float]] = {
            chunk.id: (chunk, score) for chunk, score in dense_hits
        }

        # Lexical leg (BM25)
        bm25_scores = self._bm25(workspace_id, query)

        # Union of candidates
        all_ids = set(dense_scores) | set(bm25_scores)
        chunks_by_id: dict[UUID, Chunk] = {
            cid: dense_scores[cid][0] if cid in dense_scores else self._lex[workspace_id][cid]
            for cid in all_ids
        }

        max_dense = max((s for _, s in dense_scores.values()), default=0.0) or 1.0
        max_bm25 = max(bm25_scores.values(), default=0.0) or 1.0

        results: list[RetrievalResult] = []
        for cid in all_ids:
            dense = dense_scores.get(cid, (chunks_by_id[cid], 0.0))[1]
            lex = bm25_scores.get(cid, 0.0)
            # Dense uses cosine similarity which is in [-1, 1]; clamp to [0, 1].
            dense_norm = max(0.0, min(1.0, dense / max_dense)) if max_dense else 0.0
            bm25_norm = lex / max_bm25 if max_bm25 else 0.0
            score = alpha * bm25_norm + (1 - alpha) * dense_norm
            results.append(
                RetrievalResult(
                    chunk=chunks_by_id[cid],
                    score=score,
                    bm25_score=bm25_norm,
                    dense_score=dense_norm,
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    # ------------------------------------------------------------------- BM25

    def _bm25(self, workspace_id: UUID, query: str) -> dict[UUID, float]:
        """Tiny BM25 over the in-memory lexical index. k1=1.5, b=0.75."""
        bucket = self._lex.get(workspace_id, {})
        if not bucket:
            return {}
        q_tokens = _tokens(query)
        if not q_tokens:
            return {}

        n_docs = len(bucket)
        # docfreq per term
        df: Counter[str] = Counter()
        chunk_tokens: dict[UUID, list[str]] = {}
        total_len = 0
        for cid, chunk in bucket.items():
            toks = _tokens(chunk.text)
            chunk_tokens[cid] = toks
            total_len += len(toks)
            df.update(set(toks))
        avgdl = (total_len / n_docs) if n_docs else 0.0

        k1, b = 1.5, 0.75
        scores: dict[UUID, float] = {}
        for cid, toks in chunk_tokens.items():
            if not toks:
                continue
            tf = Counter(toks)
            doc_len = len(toks)
            score = 0.0
            for term in q_tokens:
                if term not in tf:
                    continue
                idf = math.log(1 + (n_docs - df[term] + 0.5) / (df[term] + 0.5))
                num = tf[term] * (k1 + 1)
                den = tf[term] + k1 * (1 - b + b * doc_len / max(avgdl, 1.0))
                score += idf * (num / den)
            if score > 0:
                scores[cid] = score
        return scores


def _tokens(text: str) -> list[str]:
    return [m.group(0).lower() for m in _TOKEN.finditer(text)]


def _stable_iter(items: Iterable[Any]) -> list[Any]:  # pragma: no cover
    return list(items)


__all__ = ["KnowledgeBase", "RetrievalResult"]
