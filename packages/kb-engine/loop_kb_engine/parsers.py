"""Document parsers and their registry (S191 / S194).

Each parser turns raw bytes into a `Document`. The registry maps file
extensions to the concrete parser the ingest pipeline should use.

The Protocol is intentionally minimal so that downstream PDF / DOCX
parsers (S192 / S195) can be added without touching this module: they
register themselves at import time.

Only stdlib + pydantic are used; richer extractors (pypdf, BeautifulSoup,
python-docx) live in optional sibling modules so the core ``loop_kb_engine``
package stays dependency-light.
"""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable
from uuid import UUID

from loop_kb_engine.models import Document


class UnsupportedDocumentType(ValueError):  # noqa: N818 - public type name predates rule
    """Raised when no parser is registered for an extension."""


class DocumentParseError(ValueError):
    """Raised when a registered parser cannot parse the input."""


@runtime_checkable
class Parser(Protocol):
    """Bytes -> Document.

    Implementations must be stateless / re-entrant: the registry hands the
    same instance back to multiple callers concurrently.
    """

    name: str

    def parse(
        self,
        data: bytes,
        *,
        workspace_id: UUID,
        title: str,
        source: str = "",
    ) -> Document: ...


class ParserRegistry:
    """Maps file extensions (".md", ".txt") to a parser instance.

    Lookup is case-insensitive and tolerates a leading dot. Re-registering an
    extension replaces the prior parser; this is intentional so test suites
    can swap in fakes without juggling globals.
    """

    def __init__(self) -> None:
        self._parsers: dict[str, Parser] = {}

    @staticmethod
    def _normalise(extension: str) -> str:
        if not extension:
            raise ValueError("extension must be non-empty")
        ext = extension.lower()
        if not ext.startswith("."):
            ext = "." + ext
        return ext

    def register(self, extension: str, parser: Parser) -> None:
        self._parsers[self._normalise(extension)] = parser

    def lookup(self, extension: str) -> Parser:
        ext = self._normalise(extension)
        try:
            return self._parsers[ext]
        except KeyError as exc:
            raise UnsupportedDocumentType(
                f"no parser registered for extension {ext!r}"
            ) from exc

    def supported(self) -> tuple[str, ...]:
        return tuple(sorted(self._parsers))


# --------------------------------------------------------------------------- #
# S194 -- text / markdown parser with optional YAML frontmatter.
# --------------------------------------------------------------------------- #

_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<meta>.*?)\n---\s*\n(?P<body>.*)\Z",
    re.DOTALL,
)


def _parse_frontmatter_block(block: str) -> dict[str, str]:
    """Parse a tiny YAML-style ``key: value`` mapping.

    We deliberately avoid pulling in PyYAML for this so the kb-engine core
    stays dependency-light: frontmatter is overwhelmingly flat ``key: value``
    pairs in practice. Anything richer (lists, nested mappings) is not
    supported and the value is captured verbatim as a string so callers can
    still read the raw text.
    """

    out: dict[str, str] = {}
    for raw_line in block.splitlines():
        line = raw_line.rstrip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise DocumentParseError(
                f"frontmatter line missing ':' separator: {raw_line!r}"
            )
        key, _, value = line.partition(":")
        key = key.strip()
        if not key:
            raise DocumentParseError(
                f"frontmatter line with empty key: {raw_line!r}"
            )
        value = value.strip()
        # Strip matching surrounding quotes for friendliness.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        out[key] = value
    return out


class TextParser:
    """Parse plain ``.txt`` / ``.md`` content with optional frontmatter.

    * UTF-8 decoded with ``errors='strict'``; bad bytes raise.
    * Leading ``---\\n...---\\n`` block becomes ``Document.metadata``.
    * Body text is preserved verbatim (no smart trimming) so chunkers can
      apply their own boundary logic deterministically.
    """

    name = "text"

    def parse(
        self,
        data: bytes,
        *,
        workspace_id: UUID,
        title: str,
        source: str = "",
    ) -> Document:
        try:
            raw = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DocumentParseError("input is not valid utf-8") from exc
        metadata: dict[str, str] = {}
        body = raw
        m = _FRONTMATTER_RE.match(raw)
        if m is not None:
            metadata = _parse_frontmatter_block(m.group("meta"))
            body = m.group("body")
        return Document(
            workspace_id=workspace_id,
            title=title,
            text=body,
            source=source,
            metadata=metadata,
        )


def default_registry() -> ParserRegistry:
    """A registry pre-populated with the parsers shipped in core.

    Callers that want PDF / DOCX should construct their own registry and
    register those parsers from the optional sibling modules.
    """

    reg = ParserRegistry()
    text = TextParser()
    reg.register(".txt", text)
    reg.register(".md", text)
    reg.register(".markdown", text)
    return reg


__all__ = [
    "DocumentParseError",
    "Parser",
    "ParserRegistry",
    "TextParser",
    "UnsupportedDocumentType",
    "default_registry",
]
