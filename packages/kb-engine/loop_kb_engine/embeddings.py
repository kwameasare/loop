"""Embedding service abstraction.

Real impls (OpenAI, Cohere, Voyage) live behind the loop-gateway's
embeddings endpoint when added. Here we ship the Protocol and a
deterministic test embedder so the retrieval code path is fully
exercised without an LLM.
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingService(Protocol):
    @property
    def dimensions(self) -> int: ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class DeterministicEmbeddingService:
    """Hash-based embedder. Identical inputs map to identical vectors;
    similar prefixes share leading dimensions. NOT for production --
    use only in tests + the studio dev runner."""

    def __init__(self, dimensions: int = 64) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self._dim = dimensions

    @property
    def dimensions(self) -> int:
        return self._dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # Stretch / wrap the 32-byte digest to fill ``dim`` floats.
        out: list[float] = []
        for i in range(self._dim):
            byte = digest[i % len(digest)]
            # Map [0, 255] -> [-1, 1].
            out.append((byte / 127.5) - 1.0)
        # L2 normalise so cosine similarity reduces to dot product.
        norm = math.sqrt(sum(v * v for v in out))
        return [v / norm for v in out] if norm else out


__all__ = ["DeterministicEmbeddingService", "EmbeddingService"]
