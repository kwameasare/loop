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


__all__ = ["Chunk", "Document"]
