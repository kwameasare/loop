"""PDF parser (S192).

The kb-engine core is dependency-light by design (HANDBOOK: keep the import
graph for ``loop_kb_engine`` to stdlib + pydantic) so the optional pypdf
import lives behind a backend Protocol. Tests exercise the structural
``parse_pages()`` path directly with hand-rolled ``PdfPage`` lists; runtime
callers pass raw bytes via ``parse()`` which lazily imports pypdf.

Per-page metadata is preserved with a deterministic page marker so
downstream chunkers can split on it without a second parse pass. The
``Document.metadata`` map carries ``page_count`` and any pypdf-surfaced
``/Title`` / ``/Author`` keys (lowercased, dot-stripped).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from uuid import UUID

from loop_kb_engine.models import Document
from loop_kb_engine.parsers import DocumentParseError

PAGE_MARKER_TEMPLATE = "\n\n--- page {page_no} ---\n\n"


@dataclass(frozen=True, slots=True)
class PdfPage:
    """A single extracted PDF page. ``page_no`` is 1-indexed (matches pypdf)."""

    page_no: int
    text: str

    def __post_init__(self) -> None:
        if self.page_no < 1:
            raise ValueError(f"page_no must be >=1, got {self.page_no}")


@runtime_checkable
class PdfBackend(Protocol):
    """Bytes -> (pages, metadata).

    The default backend imports pypdf lazily inside ``extract()`` so the
    library is only required when parsing real PDFs at runtime.
    """

    def extract(self, data: bytes) -> tuple[tuple[PdfPage, ...], dict[str, str]]: ...


class _PypdfBackend:
    """Default backend: ``pypdf.PdfReader``. Lazily imported."""

    def extract(self, data: bytes) -> tuple[tuple[PdfPage, ...], dict[str, str]]:
        try:
            from io import BytesIO

            from pypdf import PdfReader  # type: ignore[import-not-found]
            from pypdf.errors import PdfReadError  # type: ignore[import-not-found]
        except ImportError as exc:
            raise DocumentParseError(
                "pypdf is required for PDF parsing; install loop-kb-engine[pdf]"
            ) from exc
        try:
            reader = PdfReader(BytesIO(data))
            pages: list[PdfPage] = []
            for idx, page in enumerate(reader.pages, start=1):
                pages.append(PdfPage(page_no=idx, text=(page.extract_text() or "").strip()))
            meta: dict[str, str] = {}
            info = getattr(reader, "metadata", None)
            if info:
                for key in ("/Title", "/Author", "/Subject"):
                    val = info.get(key)
                    if val:
                        meta[key.lstrip("/").lower()] = str(val)
            return tuple(pages), meta
        except PdfReadError as exc:  # corrupt / encrypted
            raise DocumentParseError(f"pdf is unreadable: {exc}") from exc


def join_pages(pages: tuple[PdfPage, ...]) -> str:
    """Join page texts using the deterministic page marker.

    Empty page text is preserved (the marker still emitted) so chunk indices
    stay stable across re-parses of the same input.
    """
    if not pages:
        return ""
    parts: list[str] = []
    for p in pages:
        parts.append(PAGE_MARKER_TEMPLATE.format(page_no=p.page_no))
        parts.append(p.text)
    return "".join(parts).lstrip()


class PdfParser:
    """``Parser`` impl for ``.pdf`` documents."""

    name = "pdf"

    def __init__(self, *, backend: PdfBackend | None = None) -> None:
        self._backend: PdfBackend = backend or _PypdfBackend()

    def parse(
        self,
        data: bytes,
        *,
        workspace_id: UUID,
        title: str,
        source: str = "",
    ) -> Document:
        if not data:
            raise DocumentParseError("pdf bytes are empty")
        pages, raw_meta = self._backend.extract(data)
        return self.parse_pages(
            pages,
            workspace_id=workspace_id,
            title=title,
            source=source,
            extra_metadata=raw_meta,
        )

    def parse_pages(
        self,
        pages: tuple[PdfPage, ...],
        *,
        workspace_id: UUID,
        title: str,
        source: str = "",
        extra_metadata: dict[str, str] | None = None,
    ) -> Document:
        """Build a ``Document`` from an already-extracted page list.

        Public so callers (and tests) can drive the parser without the
        pypdf dependency. Page numbers must be unique and strictly
        increasing; gaps are allowed (occasional skipped pages).
        """
        seen: set[int] = set()
        prev = 0
        for p in pages:
            if p.page_no in seen:
                raise DocumentParseError(f"duplicate page_no {p.page_no}")
            if p.page_no <= prev:
                raise DocumentParseError(
                    f"pages must be strictly increasing; got {p.page_no} after {prev}"
                )
            seen.add(p.page_no)
            prev = p.page_no
        meta = dict(extra_metadata or {})
        meta["page_count"] = str(len(pages))
        return Document(
            workspace_id=workspace_id,
            title=title,
            text=join_pages(pages),
            source=source,
            metadata=meta,
        )


__all__ = [
    "PAGE_MARKER_TEMPLATE",
    "PdfBackend",
    "PdfPage",
    "PdfParser",
    "join_pages",
]
