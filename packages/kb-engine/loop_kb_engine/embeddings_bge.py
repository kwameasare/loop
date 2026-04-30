"""BGE-large local embedding adapter (S201).

CI cannot pull a real ``BAAI/bge-large-en-v1.5`` checkpoint, so this
module ships a ``BgeLocalEmbeddingService`` that takes an *injected*
encoder Protocol. Production wires the encoder to ``sentence_transformers``
in a separate bindings module; tests inject a deterministic fake.

The point of S201 is to prove the adapter works without network access:
the encoder runs in-process. We assert that the dimensions advertised
by the encoder match the configured model card and reject mismatched
returns at runtime so a misconfigured deployment fails fast.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

DEFAULT_MODEL = "BAAI/bge-large-en-v1.5"

MODEL_DIMENSIONS: dict[str, int] = {
    "BAAI/bge-large-en-v1.5": 1024,
    "BAAI/bge-base-en-v1.5": 768,
    "BAAI/bge-small-en-v1.5": 384,
}


class EncoderDimensionError(RuntimeError):
    """The encoder returned a vector that does not match the model card."""


@runtime_checkable
class LocalEncoder(Protocol):
    """Sync, in-process text -> vector encoder.

    Sentence-transformers models satisfy this naturally:
    ``encode([t1, t2], normalize_embeddings=True) -> ndarray[N, D]``. The
    Protocol is sync because BGE inference holds the Python GIL anyway;
    the adapter wraps it in ``asyncio.to_thread`` to keep the public
    ``embed()`` async without blocking the event loop.
    """

    def encode(self, texts: list[str]) -> list[list[float]]: ...


class BgeLocalEmbeddingService:
    """``EmbeddingService`` impl that runs a local BGE encoder."""

    def __init__(
        self,
        *,
        encoder: LocalEncoder,
        model: str = DEFAULT_MODEL,
    ) -> None:
        if model not in MODEL_DIMENSIONS:
            raise ValueError(
                f"unknown bge model {model!r}; known: {sorted(MODEL_DIMENSIONS)}"
            )
        self._encoder = encoder
        self._model = model

    @property
    def dimensions(self) -> int:
        return MODEL_DIMENSIONS[self._model]

    @property
    def model(self) -> str:
        return self._model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        import asyncio

        vectors = await asyncio.to_thread(self._encoder.encode, list(texts))
        if len(vectors) != len(texts):
            raise EncoderDimensionError(
                f"encoder returned {len(vectors)} vectors for {len(texts)} inputs"
            )
        out: list[list[float]] = []
        for i, vec in enumerate(vectors):
            if len(vec) != self.dimensions:
                raise EncoderDimensionError(
                    f"row {i}: expected dim {self.dimensions}, got {len(vec)}"
                )
            out.append([float(x) for x in vec])
        return out


__all__ = [
    "DEFAULT_MODEL",
    "MODEL_DIMENSIONS",
    "BgeLocalEmbeddingService",
    "EncoderDimensionError",
    "LocalEncoder",
]
