"""HTML parser (S193).

Stdlib-only readability extraction. We strip nav/footer/aside/script/style
elements, prefer ``<main>`` / ``<article>`` if present, and emit headings
with markdown ``#`` prefixes so chunkers can use them as natural boundaries.

The parser intentionally does not pull BeautifulSoup. ``html.parser.HTMLParser``
plus a small DOM-light state machine handles the well-formed inputs from
the kb ingest pipeline (which receives sanitised content via the upstream
crawler). For pathological inputs we raise ``DocumentParseError`` rather
than silently producing garbage.
"""

from __future__ import annotations

from html import unescape
from html.parser import HTMLParser as _StdlibHTMLParser
from uuid import UUID

from loop_kb_engine.models import Document
from loop_kb_engine.parsers import DocumentParseError

#: Block-level tags the parser inserts paragraph breaks around.
BLOCK_TAGS: frozenset[str] = frozenset(
    {
        "p", "div", "section", "article", "li", "tr", "td", "th",
        "blockquote", "pre", "h1", "h2", "h3", "h4", "h5", "h6",
        "main", "header", "footer", "br", "hr",
    }
)

#: Tags whose contents are dropped wholesale (boilerplate / non-content).
DROP_TAGS: frozenset[str] = frozenset(
    {"script", "style", "nav", "aside", "footer", "noscript", "form"}
)

#: Tags that mark "main content" \u2014 if present, the parser only emits
#: text from inside one of these. Order matters: first match wins.
MAIN_TAGS: tuple[str, ...] = ("main", "article")

HEADING_TAGS: tuple[str, ...] = ("h1", "h2", "h3", "h4", "h5", "h6")


class _Extractor(_StdlibHTMLParser):
    """Walk the DOM, accumulate prose, drop boilerplate tag subtrees."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._buf: list[str] = []
        self._drop_depth = 0
        self._main_depth = 0
        self._has_main = False
        self._heading: str | None = None
        self.title: str | None = None
        self._in_title = False

    def emit(self, text: str) -> None:
        if self._main_required and self._main_depth == 0:
            return
        if self._drop_depth:
            return
        self._buf.append(text)

    @property
    def _main_required(self) -> bool:
        return self._has_main

    def feed_html(self, src: str) -> str:
        # Pre-scan so we know whether the document has a <main>/<article>.
        lowered = src.lower()
        self._has_main = any(f"<{t}" in lowered for t in MAIN_TAGS)
        self.feed(src)
        self.close()
        text = "".join(self._buf)
        # Collapse runs of blank lines to a single blank \u2014 keeps chunk
        # boundaries deterministic across re-parses of the same input.
        out_lines: list[str] = []
        blank = 0
        for line in text.splitlines():
            line = line.rstrip()
            if not line:
                blank += 1
                if blank <= 1:
                    out_lines.append("")
                continue
            blank = 0
            out_lines.append(line)
        return "\n".join(out_lines).strip()

    # --- HTMLParser hooks --------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = True
            return
        if tag in DROP_TAGS:
            self._drop_depth += 1
            return
        if tag in MAIN_TAGS:
            self._main_depth += 1
        if tag in HEADING_TAGS:
            self._heading = tag
            self.emit("\n\n" + "#" * int(tag[1]) + " ")
            return
        if tag in BLOCK_TAGS:
            self.emit("\n\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
            return
        if tag in DROP_TAGS:
            self._drop_depth = max(0, self._drop_depth - 1)
            return
        if tag in MAIN_TAGS:
            self._main_depth = max(0, self._main_depth - 1)
        if tag in HEADING_TAGS:
            self._heading = None
            self.emit("\n")
            return
        if tag in BLOCK_TAGS:
            self.emit("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            if self.title is None:
                self.title = unescape(data).strip()
            return
        self.emit(data)


class HtmlParser:
    """``Parser`` impl for ``.html`` / ``.htm`` documents."""

    name = "html"

    def parse(
        self,
        data: bytes,
        *,
        workspace_id: UUID,
        title: str,
        source: str = "",
    ) -> Document:
        if not data:
            raise DocumentParseError("html bytes are empty")
        try:
            raw = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DocumentParseError("html is not valid utf-8") from exc
        return self.parse_text(
            raw,
            workspace_id=workspace_id,
            title=title,
            source=source,
        )

    def parse_text(
        self,
        raw: str,
        *,
        workspace_id: UUID,
        title: str,
        source: str = "",
    ) -> Document:
        extractor = _Extractor()
        body = extractor.feed_html(raw)
        meta: dict[str, str] = {}
        if extractor.title:
            meta["html_title"] = extractor.title
        return Document(
            workspace_id=workspace_id,
            title=title,
            text=body,
            source=source,
            metadata=meta,
        )


__all__ = [
    "BLOCK_TAGS",
    "DROP_TAGS",
    "HEADING_TAGS",
    "MAIN_TAGS",
    "HtmlParser",
]
