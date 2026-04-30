"""Voyage AI (voyage-3) embedding adapter (S200).

Concrete ``EmbeddingService`` impl over Voyage's REST API. The HTTP
client is injected via a tiny Protocol so tests can supply a fake without
network. The adapter normalises the response shape (dict ordering,
``voyage-3`` vs. ``voyage-3-large``) and raises ``EmbeddingProviderError``
on any non-2xx response.

Per ADR-002 (cloud-portability), no ``httpx``/``requests`` import lives at
module top-level: the caller injects an ``HttpClient`` Protocol, the
production impl is a thin ``httpx.AsyncClient`` wrapper kept in the
gateway's bindings package.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"
DEFAULT_MODEL = "voyage-3"

#: Per Voyage's published model card. Update if Voyage rolls a new dim.
MODEL_DIMENSIONS: dict[str, int] = {
    "voyage-3": 1024,
    "voyage-3-large": 1024,
    "voyage-3-lite": 512,
    "voyage-code-3": 1024,
}


class EmbeddingProviderError(RuntimeError):
    """Voyage replied with a non-2xx or an unparseable body."""


@runtime_checkable
class HttpClient(Protocol):
    async def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> tuple[int, dict[str, Any]]: ...


class VoyageEmbeddingService:
    """``embed(texts) -> list[vector]`` over Voyage's REST API."""

    def __init__(
        self,
        *,
        api_key: str,
        http: HttpClient,
        model: str = DEFAULT_MODEL,
        url: str = VOYAGE_API_URL,
        input_type: str = "document",
    ) -> None:
        if not api_key:
            raise ValueError("api_key must be non-empty")
        if model not in MODEL_DIMENSIONS:
            raise ValueError(
                f"unknown voyage model {model!r}; known: {sorted(MODEL_DIMENSIONS)}"
            )
        if input_type not in ("document", "query"):
            raise ValueError("input_type must be 'document' or 'query'")
        self._api_key = api_key
        self._http = http
        self._model = model
        self._url = url
        self._input_type = input_type

    @property
    def dimensions(self) -> int:
        return MODEL_DIMENSIONS[self._model]

    @property
    def model(self) -> str:
        return self._model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        for t in texts:
            if not isinstance(t, str):
                raise TypeError("texts must be a list of str")
        body: dict[str, Any] = {
            "input": texts,
            "model": self._model,
            "input_type": self._input_type,
        }
        headers = {
            "authorization": f"Bearer {self._api_key}",
            "content-type": "application/json",
        }
        status, payload = await self._http.post_json(self._url, headers=headers, body=body)
        if status < 200 or status >= 300:
            raise EmbeddingProviderError(f"voyage returned {status}: {payload!r}")
        try:
            data = payload["data"]
        except (KeyError, TypeError) as exc:
            raise EmbeddingProviderError(f"voyage response missing 'data': {payload!r}") from exc
        if not isinstance(data, list) or len(data) != len(texts):
            raise EmbeddingProviderError(
                f"voyage returned {len(data) if isinstance(data, list) else '?'} embeddings "
                f"for {len(texts)} inputs"
            )
        out: list[list[float]] = []
        for idx, item in enumerate(data):
            try:
                vec = item["embedding"]
            except (KeyError, TypeError) as exc:
                raise EmbeddingProviderError(f"voyage row {idx} missing 'embedding'") from exc
            if not isinstance(vec, list) or len(vec) != self.dimensions:
                raise EmbeddingProviderError(
                    f"voyage row {idx} dim mismatch: got {len(vec) if isinstance(vec, list) else '?'} "
                    f"expected {self.dimensions}"
                )
            out.append([float(x) for x in vec])
        return out


__all__ = [
    "DEFAULT_MODEL",
    "MODEL_DIMENSIONS",
    "VOYAGE_API_URL",
    "EmbeddingProviderError",
    "HttpClient",
    "VoyageEmbeddingService",
]
