"""Document chunking strategies.

Both chunkers implement the structural ``Chunker`` protocol:
``chunk(document) -> list[Chunk]``. Production chunking quality is
out of scope here; this is the v0 interface so the rest of the
pipeline can be built and tested.
"""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from loop_kb_engine.models import Chunk, Document


@runtime_checkable
class Chunker(Protocol):
    def chunk(self, document: Document) -> list[Chunk]: ...


class FixedSizeChunker:
    """Naive char-window chunker with overlap."""

    def __init__(self, *, chunk_size: int = 500, overlap: int = 50) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be >= 0 and < chunk_size")
        self._size = chunk_size
        self._overlap = overlap

    def chunk(self, document: Document) -> list[Chunk]:
        text = document.text
        if not text:
            return []
        step = self._size - self._overlap
        chunks: list[Chunk] = []
        ordinal = 0
        start = 0
        while start < len(text):
            end = min(start + self._size, len(text))
            piece = text[start:end].strip()
            if piece:
                chunks.append(
                    Chunk(
                        document_id=document.id,
                        workspace_id=document.workspace_id,
                        ordinal=ordinal,
                        text=piece,
                    )
                )
                ordinal += 1
            if end == len(text):
                break
            start += step
        return chunks


_PARA_BOUNDARY = re.compile(r"\n\s*\n")


class SemanticChunker:
    """Boundary-aware: splits on paragraph breaks, then merges to
    keep each chunk within ``max_chars``. ADR-019 says we honour
    semantic boundaries by default."""

    def __init__(self, *, max_chars: int = 800) -> None:
        if max_chars <= 0:
            raise ValueError("max_chars must be positive")
        self._max = max_chars

    def chunk(self, document: Document) -> list[Chunk]:
        if not document.text:
            return []
        paragraphs = [p.strip() for p in _PARA_BOUNDARY.split(document.text)]
        paragraphs = [p for p in paragraphs if p]

        merged: list[str] = []
        current = ""
        for para in paragraphs:
            if not current:
                current = para
                continue
            candidate = f"{current}\n\n{para}"
            if len(candidate) <= self._max:
                current = candidate
            else:
                merged.append(current)
                current = para
        if current:
            merged.append(current)

        return [
            Chunk(
                document_id=document.id,
                workspace_id=document.workspace_id,
                ordinal=i,
                text=text,
            )
            for i, text in enumerate(merged)
        ]


__all__ = ["Chunker", "FixedSizeChunker", "SemanticChunker"]
