"""Reranker (S206).

Cross-encoder rerankers re-score a candidate list against a query and
return them sorted by relevance. We use a structural Protocol so callers
can swap Cohere ``rerank-3`` for a local cross-encoder without changing
the retrieval pipeline.

Two impls ship:

1. ``CohereReranker`` \u2014 production, calls Cohere via an injected
   ``HttpClient`` (same Protocol as the Voyage adapter).
2. ``LexicalOverlapReranker`` \u2014 dependency-free fallback that ranks
   by Jaccard token overlap. It is intentionally weaker than a real
   cross-encoder; it exists for unit tests, ablation evals, and
   air-gapped deployments where Cohere is not reachable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

COHERE_API_URL = "https://api.cohere.com/v2/rerank"
DEFAULT_MODEL = "rerank-3.5"

_TOKEN_RE = re.compile(r"[\w']+")


@dataclass(frozen=True, slots=True)
class RerankHit:
    """One candidate to be reranked.

    The reranker is opaque about the underlying record \u2014 callers
    pass an arbitrary id, we hand it back in the new order.
    """

    id: str
    text: str
    score: float = 0.0


class RerankError(RuntimeError):
    """Reranker upstream returned an unexpected payload."""


@runtime_checkable
class HttpClient(Protocol):
    async def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> tuple[int, dict[str, Any]]: ...


@runtime_checkable
class Reranker(Protocol):
    """Re-score a list of hits against a query."""

    async def rerank(
        self,
        query: str,
        hits: list[RerankHit],
        *,
        top_n: int | None = None,
    ) -> list[RerankHit]: ...


class CohereReranker:
    """Cohere ``rerank-3`` reranker."""

    def __init__(
        self,
        *,
        api_key: str,
        http: HttpClient,
        model: str = DEFAULT_MODEL,
        url: str = COHERE_API_URL,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must be non-empty")
        self._api_key = api_key
        self._http = http
        self._model = model
        self._url = url

    async def rerank(
        self,
        query: str,
        hits: list[RerankHit],
        *,
        top_n: int | None = None,
    ) -> list[RerankHit]:
        if not hits:
            return []
        body: dict[str, Any] = {
            "model": self._model,
            "query": query,
            "documents": [h.text for h in hits],
        }
        if top_n is not None:
            if top_n < 1:
                raise ValueError("top_n must be >=1")
            body["top_n"] = min(top_n, len(hits))
        headers = {
            "authorization": f"Bearer {self._api_key}",
            "content-type": "application/json",
        }
        status, payload = await self._http.post_json(self._url, headers=headers, body=body)
        if status < 200 or status >= 300:
            raise RerankError(f"cohere returned {status}: {payload!r}")
        try:
            results = payload["results"]
        except (KeyError, TypeError) as exc:
            raise RerankError(f"cohere response missing 'results': {payload!r}") from exc
        out: list[RerankHit] = []
        for row in results:
            try:
                idx = int(row["index"])
                score = float(row["relevance_score"])
            except (KeyError, TypeError, ValueError) as exc:
                raise RerankError(f"cohere row malformed: {row!r}") from exc
            if not 0 <= idx < len(hits):
                raise RerankError(f"cohere index out of range: {idx}")
            original = hits[idx]
            out.append(RerankHit(id=original.id, text=original.text, score=score))
        return out


class LexicalOverlapReranker:
    """Dependency-free Jaccard-overlap reranker.

    Useful for tests and air-gapped envs. Strictly weaker than Cohere
    \u2014 callers should treat it as a baseline, not a substitute.
    """

    async def rerank(
        self,
        query: str,
        hits: list[RerankHit],
        *,
        top_n: int | None = None,
    ) -> list[RerankHit]:
        if not hits:
            return []
        q_tokens = _tokens(query)
        scored: list[RerankHit] = []
        for h in hits:
            t = _tokens(h.text)
            if not q_tokens or not t:
                score = 0.0
            else:
                inter = len(q_tokens & t)
                union = len(q_tokens | t)
                score = inter / union if union else 0.0
            scored.append(RerankHit(id=h.id, text=h.text, score=score))
        scored.sort(key=lambda x: x.score, reverse=True)
        if top_n is not None:
            if top_n < 1:
                raise ValueError("top_n must be >=1")
            scored = scored[:top_n]
        return scored


def _tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN_RE.finditer(text)}


__all__ = [
    "COHERE_API_URL",
    "DEFAULT_MODEL",
    "CohereReranker",
    "HttpClient",
    "LexicalOverlapReranker",
    "RerankError",
    "RerankHit",
    "Reranker",
]
