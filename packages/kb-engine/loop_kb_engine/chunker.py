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


_HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<title>.+?)\s*#*\s*$")


class HeadingChunker:
    """Split a markdown document on its headings (S198).

    Each top-level (``#``) heading starts a fresh chunk. Sub-headings
    (``##``..``######``) stay inside their parent chunk, but their text is
    captured into ``Chunk.metadata['context']`` as a ``"breadcrumb > path"``
    so retrievers can present rich provenance.

    Documents with no headings degrade gracefully to a single chunk
    containing the original text. This keeps the chunker safe to wire in
    front of any text source without a content guard.
    """

    def __init__(self, *, top_level: int = 1) -> None:
        if not (1 <= top_level <= 6):
            raise ValueError("top_level must be between 1 and 6")
        self._top = top_level

    def chunk(self, document: Document) -> list[Chunk]:
        text = document.text
        if not text.strip():
            return []

        lines = text.splitlines()
        sections: list[tuple[str, list[str], list[str]]] = []
        # (heading_title, breadcrumb_path, body_lines)
        current_title = ""
        current_path: list[str] = []
        current_body: list[str] = []
        # Track sub-headings encountered since the last top-level split so
        # their context can be attached to the current section.
        sub_path: list[tuple[int, str]] = []

        def _flush() -> None:
            if current_title or "\n".join(current_body).strip():
                sections.append(
                    (current_title, list(current_path), list(current_body))
                )

        seen_top = False
        for raw in lines:
            m = _HEADING_RE.match(raw)
            if m is None:
                current_body.append(raw)
                continue
            level = len(m.group("hashes"))
            heading = m.group("title").strip()
            if level == self._top:
                if seen_top or current_body:
                    _flush()
                seen_top = True
                current_title = heading
                sub_path = []
                current_path = [heading]
                current_body = []
            elif level > self._top:
                # Drop deeper sub-headings off the path before pushing.
                while sub_path and sub_path[-1][0] >= level:
                    sub_path.pop()
                sub_path.append((level, heading))
                current_path = (
                    [current_title] if current_title else []
                ) + [h for _, h in sub_path]
                current_body.append(raw)
            else:
                # Heading level shallower than top -- treat as plain text so
                # we never silently drop content.
                current_body.append(raw)
        _flush()

        chunks: list[Chunk] = []
        for ordinal, (title, path, body) in enumerate(sections):
            body_text = "\n".join(body).strip()
            if not body_text and not title:
                continue
            text_blob = f"{('#' * self._top)} {title}\n\n{body_text}".strip() if title else body_text
            metadata: dict[str, str] = {}
            if path:
                metadata["context"] = " > ".join(path)
            if title:
                metadata["heading"] = title
            chunks.append(
                Chunk(
                    document_id=document.id,
                    workspace_id=document.workspace_id,
                    ordinal=ordinal,
                    text=text_blob,
                    metadata=metadata,
                )
            )
        return chunks


__all__ = [
    "Chunker",
    "FixedSizeChunker",
    "HeadingChunker",
    "SemanticChunker",
]
