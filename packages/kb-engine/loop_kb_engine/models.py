"""Strict pydantic v2 models for KB documents and chunks."""

from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Document(_StrictModel):
    """A source document. Bytes/PDF parsing happens upstream."""

    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    title: str
    text: str
    source: str = ""  # filename, URL, etc.
    metadata: dict[str, str] = Field(default_factory=dict)


class Chunk(_StrictModel):
    """A retrieval unit. Stable id derived from document + offset."""

    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    workspace_id: UUID
    ordinal: int = Field(ge=0)
    text: str
    metadata: dict[str, str] = Field(default_factory=dict)


class EmbeddingVector(_StrictModel):
    """A dense embedding tied to a chunk.

    Validates dimensionality and rejects non-finite components so callers
    cannot accidentally persist NaN/Inf into a vector store.
    """

    chunk_id: UUID
    workspace_id: UUID
    model: str = Field(min_length=1)
    values: tuple[float, ...] = Field(min_length=1)

    @classmethod
    def of(
        cls,
        *,
        chunk: Chunk,
        model: str,
        values: tuple[float, ...] | list[float],
    ) -> EmbeddingVector:
        coerced = tuple(float(v) for v in values)
        for v in coerced:
            # Reject NaN and +/-inf explicitly: pydantic accepts them by default.
            if v != v or v in (float("inf"), float("-inf")):
                raise ValueError("embedding values must be finite")
        return cls(
            chunk_id=chunk.id,
            workspace_id=chunk.workspace_id,
            model=model,
            values=coerced,
        )

    @property
    def dim(self) -> int:
        return len(self.values)


__all__ = ["Chunk", "Document", "EmbeddingVector"]
