"""Tests for parsers (S191/S194) and the heading chunker (S198)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from loop_kb_engine import (
    Document,
    DocumentParseError,
    HeadingChunker,
    ParserRegistry,
    TextParser,
    UnsupportedDocumentType,
    default_registry,
)

# --------------------------------------------------------------------------- #
# S191 -- Parser registry
# --------------------------------------------------------------------------- #


def test_registry_normalises_extension_and_returns_parser() -> None:
    reg = ParserRegistry()
    parser = TextParser()
    reg.register("MD", parser)  # uppercase, no leading dot
    assert reg.lookup(".md") is parser
    assert reg.lookup("md") is parser
    assert ".md" in reg.supported()


def test_registry_unsupported_extension_raises() -> None:
    reg = ParserRegistry()
    with pytest.raises(UnsupportedDocumentType):
        reg.lookup(".pdf")


def test_registry_rejects_empty_extension() -> None:
    reg = ParserRegistry()
    with pytest.raises(ValueError):
        reg.register("", TextParser())


def test_default_registry_covers_text_and_markdown() -> None:
    reg = default_registry()
    assert set(reg.supported()) >= {".txt", ".md", ".markdown"}


# --------------------------------------------------------------------------- #
# S194 -- text / markdown parser with frontmatter
# --------------------------------------------------------------------------- #


def test_text_parser_plain_text() -> None:
    ws = uuid4()
    p = TextParser()
    doc = p.parse(b"hello world", workspace_id=ws, title="t")
    assert isinstance(doc, Document)
    assert doc.text == "hello world"
    assert doc.metadata == {}
    assert doc.workspace_id == ws


def test_text_parser_extracts_frontmatter() -> None:
    body = b"""---
author: Ada
tags: ai, agents
title: "Quoted Title"
---
# Heading

body line.
"""
    p = TextParser()
    doc = p.parse(body, workspace_id=uuid4(), title="t")
    assert doc.metadata == {
        "author": "Ada",
        "tags": "ai, agents",
        "title": "Quoted Title",
    }
    assert doc.text.startswith("# Heading")


def test_text_parser_invalid_utf8_raises() -> None:
    p = TextParser()
    with pytest.raises(DocumentParseError):
        p.parse(b"\xff\xfe\x00bad", workspace_id=uuid4(), title="t")


def test_text_parser_malformed_frontmatter_raises() -> None:
    p = TextParser()
    body = b"---\nno-colon-line\n---\nbody\n"
    with pytest.raises(DocumentParseError):
        p.parse(body, workspace_id=uuid4(), title="t")


# --------------------------------------------------------------------------- #
# S198 -- heading chunker
# --------------------------------------------------------------------------- #


def _doc(text: str) -> Document:
    return Document(workspace_id=uuid4(), title="t", text=text)


def test_heading_chunker_splits_top_level() -> None:
    text = (
        "# Alpha\n\nbody-a line.\n\n"
        "# Beta\n\nbody-b line.\n\n"
        "# Gamma\n\nbody-g line.\n"
    )
    chunks = HeadingChunker().chunk(_doc(text))
    assert len(chunks) == 3
    assert [c.metadata["heading"] for c in chunks] == ["Alpha", "Beta", "Gamma"]
    assert "body-a" in chunks[0].text
    assert "body-b" in chunks[1].text
    assert "body-g" in chunks[2].text
    assert [c.ordinal for c in chunks] == [0, 1, 2]


def test_heading_chunker_preserves_subheading_in_context() -> None:
    text = (
        "# Top\n\nintro line.\n\n"
        "## Sub-A\n\nsub a body.\n\n"
        "### Deeper\n\ndeep body.\n\n"
        "# Next\n\nnext body.\n"
    )
    chunks = HeadingChunker().chunk(_doc(text))
    assert len(chunks) == 2
    # First chunk's context contains the deepest path seen (last sub).
    assert chunks[0].metadata["context"].startswith("Top")
    assert "Deeper" in chunks[0].metadata["context"]
    assert "## Sub-A" in chunks[0].text  # sub-headings preserved inline
    assert chunks[1].metadata["heading"] == "Next"


def test_heading_chunker_no_headings_returns_single_chunk() -> None:
    text = "just a line.\n\nanother line.\n"
    chunks = HeadingChunker().chunk(_doc(text))
    assert len(chunks) == 1
    assert "another line" in chunks[0].text
    assert "heading" not in chunks[0].metadata


def test_heading_chunker_empty_text_returns_empty() -> None:
    chunks = HeadingChunker().chunk(_doc("   \n  \n"))
    assert chunks == []


def test_heading_chunker_validates_top_level() -> None:
    with pytest.raises(ValueError):
        HeadingChunker(top_level=0)
    with pytest.raises(ValueError):
        HeadingChunker(top_level=7)


def test_heading_chunker_custom_top_level() -> None:
    text = "# h1\n\n## start\n\nfirst body.\n\n## next\n\nnext body.\n"
    chunks = HeadingChunker(top_level=2).chunk(_doc(text))
    titled = [c.metadata.get("heading") for c in chunks if "heading" in c.metadata]
    assert titled == ["start", "next"]
