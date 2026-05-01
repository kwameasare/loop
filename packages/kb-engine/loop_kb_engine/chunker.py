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
            raw_piece = text[start:end]
            piece = raw_piece.strip()
            if piece:
                leading_ws = len(raw_piece) - len(raw_piece.lstrip())
                trailing_ws = len(raw_piece) - len(raw_piece.rstrip())
                piece_start = start + leading_ws
                piece_end = end - trailing_ws
                chunks.append(
                    Chunk(
                        document_id=document.id,
                        workspace_id=document.workspace_id,
                        ordinal=ordinal,
                        text=piece,
                        metadata=_citation_metadata(document, piece_start, piece_end),
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
        paragraphs = _paragraphs_with_offsets(document.text)

        merged: list[tuple[str, int, int]] = []
        current_text = ""
        current_start = 0
        current_end = 0
        for para, para_start, para_end in paragraphs:
            if not current_text:
                current_text = para
                current_start = para_start
                current_end = para_end
                continue
            candidate = f"{current_text}\n\n{para}"
            if len(candidate) <= self._max:
                current_text = candidate
                current_end = para_end
            else:
                merged.append((current_text, current_start, current_end))
                current_text = para
                current_start = para_start
                current_end = para_end
        if current_text:
            merged.append((current_text, current_start, current_end))

        return [
            Chunk(
                document_id=document.id,
                workspace_id=document.workspace_id,
                ordinal=i,
                text=text,
                metadata=_citation_metadata(document, start, end),
            )
            for i, (text, start, end) in enumerate(merged)
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
            start = document.text.find(body_text or title)
            if start < 0:
                start = 0
            end = start + len(body_text or title)
            chunks.append(
                Chunk(
                    document_id=document.id,
                    workspace_id=document.workspace_id,
                    ordinal=ordinal,
                    text=text_blob,
                    metadata=_citation_metadata(document, start, end, extra=metadata),
                )
            )
        return chunks


def _paragraphs_with_offsets(text: str) -> list[tuple[str, int, int]]:
    paragraphs: list[tuple[str, int, int]] = []
    start = 0
    for match in _PARA_BOUNDARY.finditer(text):
        _append_paragraph(paragraphs, text, start, match.start())
        start = match.end()
    _append_paragraph(paragraphs, text, start, len(text))
    return paragraphs


def _append_paragraph(
    paragraphs: list[tuple[str, int, int]], text: str, start: int, end: int
) -> None:
    raw = text[start:end]
    piece = raw.strip()
    if not piece:
        return
    leading_ws = len(raw) - len(raw.lstrip())
    trailing_ws = len(raw) - len(raw.rstrip())
    paragraphs.append((piece, start + leading_ws, end - trailing_ws))


def _citation_metadata(
    document: Document,
    start: int,
    end: int,
    *,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    metadata = dict(document.metadata)
    if extra:
        metadata.update(extra)
    if document.source:
        metadata.setdefault("source_uri", document.source)
    if document.title:
        metadata.setdefault("title", document.title)
    safe_start = max(0, min(start, len(document.text)))
    safe_end = max(safe_start, min(end, len(document.text)))
    metadata["byte_start"] = str(len(document.text[:safe_start].encode()))
    metadata["byte_end"] = str(len(document.text[:safe_end].encode()))
    return metadata


__all__ = [
    "Chunker",
    "FixedSizeChunker",
    "HeadingChunker",
    "SemanticChunker",
]
