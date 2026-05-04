"""
S496: LayoutAwareChunker — keeps tables, fenced code blocks, and math
      blocks intact when chunking Markdown/plain text.

Strategy
--------
1. Scan the document text, identify "protected" spans:
   - Fenced code blocks (``` or ~~~)
   - GitHub-flavoured Markdown tables (lines starting with |)
   - LaTeX display math ($$...$$)
2. Split the remaining prose on paragraph breaks (same as SemanticChunker).
3. Never split inside a protected span.
4. When a protected span is encountered, flush the current prose chunk
   (if any), then emit the whole protected block as a single chunk.
5. After the protected block, continue prose merging.

Each chunk's ``metadata`` carries:
  - ``chunk_type``: "prose" | "code" | "table" | "math"
  - ``source``, ``offset_start``, ``offset_end``: citation info
"""
from __future__ import annotations

import re
from enum import StrEnum

from loop_kb_engine.models import Chunk, Document

# ---------------------------------------------------------------------------
# Chunk type tag
# ---------------------------------------------------------------------------

class ChunkType(StrEnum):
    PROSE = "prose"
    CODE = "code"
    TABLE = "table"
    MATH = "math"


# ---------------------------------------------------------------------------
# Span detection — returns ordered list of (start, end, ChunkType) for
# protected regions.  These must not overlap.
# ---------------------------------------------------------------------------

# Fenced code blocks: ``` or ~~~, optional language tag on opening fence
_FENCE_RE = re.compile(
    r"^(?P<fence>```|~~~)[^\n]*\n.*?^(?P=fence)\s*$",
    re.MULTILINE | re.DOTALL,
)

# Display math:  $$...$$  (non-greedy, multiline)
_MATH_RE = re.compile(r"\$\$.*?\$\$", re.DOTALL)

# Table blocks: one or more consecutive lines starting with | (GFM)
_TABLE_RE = re.compile(r"(?m)^(\|[^\n]*\n)+")


def _find_protected_spans(
    text: str,
) -> list[tuple[int, int, ChunkType]]:
    spans: list[tuple[int, int, ChunkType]] = []
    for m in _FENCE_RE.finditer(text):
        spans.append((m.start(), m.end(), ChunkType.CODE))
    for m in _MATH_RE.finditer(text):
        spans.append((m.start(), m.end(), ChunkType.MATH))
    for m in _TABLE_RE.finditer(text):
        spans.append((m.start(), m.end(), ChunkType.TABLE))

    # Remove overlapping spans (keep the one that starts earlier, then longer)
    spans.sort(key=lambda s: (s[0], -(s[1] - s[0])))
    deduped: list[tuple[int, int, ChunkType]] = []
    max_end = -1
    for s, e, t in spans:
        if s >= max_end:
            deduped.append((s, e, t))
            max_end = e

    return deduped


# ---------------------------------------------------------------------------
# Citation metadata helper (mirrors chunker.py convention)
# ---------------------------------------------------------------------------

def _meta(
    document: Document,
    start: int,
    end: int,
    chunk_type: ChunkType,
) -> dict[str, str]:
    return {
        "source": document.source or str(document.id),
        "offset_start": str(start),
        "offset_end": str(end),
        "chunk_type": chunk_type.value,
    }


# ---------------------------------------------------------------------------
# LayoutAwareChunker
# ---------------------------------------------------------------------------

_PARA_SEP = re.compile(r"\n\s*\n")


class LayoutAwareChunker:
    """
    Chunks Markdown text while keeping tables, code blocks, and math intact.

    Parameters
    ----------
    max_prose_chars:
        Maximum characters per prose chunk.  Protected spans (table/code/math)
        are emitted whole regardless of size.
    """

    def __init__(self, *, max_prose_chars: int = 800) -> None:
        if max_prose_chars <= 0:
            raise ValueError("max_prose_chars must be positive")
        self._max = max_prose_chars

    # ---------------------------------------------------------------- public

    def chunk(self, document: Document) -> list[Chunk]:
        text = document.text
        if not text.strip():
            return []

        protected = _find_protected_spans(text)
        segments = self._split_by_protected(text, protected)

        raw_chunks: list[tuple[int, int, ChunkType, str]] = []
        prose_buf: list[tuple[str, int, int]] = []

        def _flush_prose() -> None:
            if not prose_buf:
                return
            merged = self._merge_prose(prose_buf)
            raw_chunks.extend(merged)
            prose_buf.clear()

        for seg_start, seg_end, seg_type, seg_text in segments:
            if seg_type != ChunkType.PROSE:
                _flush_prose()
                stripped = seg_text.strip()
                if stripped:
                    raw_chunks.append((seg_start, seg_end, seg_type, stripped))
            else:
                # Split prose on paragraph breaks and buffer.
                paras = self._para_pieces(seg_text, seg_start)
                prose_buf.extend(paras)

        _flush_prose()

        return [
            Chunk(
                document_id=document.id,
                workspace_id=document.workspace_id,
                ordinal=i,
                text=text_piece,
                metadata=_meta(document, s, e, t),
            )
            for i, (s, e, t, text_piece) in enumerate(raw_chunks)
        ]

    # ---------------------------------------------------------------- private

    def _split_by_protected(
        self,
        text: str,
        protected: list[tuple[int, int, ChunkType]],
    ) -> list[tuple[int, int, ChunkType, str]]:
        """
        Interleave prose segments and protected segments in document order.
        """
        segments: list[tuple[int, int, ChunkType, str]] = []
        cursor = 0
        for p_start, p_end, p_type in protected:
            if cursor < p_start:
                prose = text[cursor:p_start]
                if prose.strip():
                    segments.append((cursor, p_start, ChunkType.PROSE, prose))
            segments.append((p_start, p_end, p_type, text[p_start:p_end]))
            cursor = p_end
        # Trailing prose after last protected span.
        if cursor < len(text):
            prose = text[cursor:]
            if prose.strip():
                segments.append((cursor, len(text), ChunkType.PROSE, prose))
        return segments

    def _para_pieces(
        self,
        prose: str,
        base_offset: int,
    ) -> list[tuple[str, int, int]]:
        """Split a prose segment into paragraphs with absolute offsets."""
        pieces: list[tuple[str, int, int]] = []
        pos = 0
        for m in _PARA_SEP.finditer(prose):
            para = prose[pos:m.start()].strip()
            if para:
                abs_start = base_offset + pos
                abs_end = base_offset + m.start()
                pieces.append((para, abs_start, abs_end))
            pos = m.end()
        tail = prose[pos:].strip()
        if tail:
            pieces.append((tail, base_offset + pos, base_offset + len(prose)))
        return pieces

    def _merge_prose(
        self,
        paras: list[tuple[str, int, int]],
    ) -> list[tuple[int, int, ChunkType, str]]:
        """Merge small paragraphs up to max_prose_chars into single chunks."""
        if not paras:
            return []
        merged: list[tuple[int, int, ChunkType, str]] = []
        cur_text, cur_start, cur_end = paras[0]
        for para, p_start, p_end in paras[1:]:
            candidate = f"{cur_text}\n\n{para}"
            if len(candidate) <= self._max:
                cur_text = candidate
                cur_end = p_end
            else:
                merged.append((cur_start, cur_end, ChunkType.PROSE, cur_text))
                cur_text, cur_start, cur_end = para, p_start, p_end
        merged.append((cur_start, cur_end, ChunkType.PROSE, cur_text))
        return merged
