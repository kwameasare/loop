"""
S496 — tests for LayoutAwareChunker.
"""
from __future__ import annotations

from uuid import uuid4

import pytest

from loop_kb_engine.layout_chunker import ChunkType, LayoutAwareChunker
from loop_kb_engine.models import Document

WS = uuid4()


def doc(text: str) -> Document:
    return Document(workspace_id=WS, title="test", text=text)


# ---------------------------------------------------------------------------
# 1. Basic prose chunking
# ---------------------------------------------------------------------------

class TestProseChunking:
    def test_returns_empty_for_empty_doc(self) -> None:
        chunker = LayoutAwareChunker()
        assert chunker.chunk(doc("")) == []
        assert chunker.chunk(doc("   \n  ")) == []

    def test_single_prose_paragraph(self) -> None:
        chunker = LayoutAwareChunker()
        result = chunker.chunk(doc("Hello world."))
        assert len(result) == 1
        assert result[0].text == "Hello world."
        assert result[0].metadata["chunk_type"] == "prose"

    def test_two_paragraphs_merged_within_limit(self) -> None:
        chunker = LayoutAwareChunker(max_prose_chars=200)
        text = "Para one.\n\nPara two."
        result = chunker.chunk(doc(text))
        assert len(result) == 1
        assert "Para one" in result[0].text
        assert "Para two" in result[0].text

    def test_prose_split_when_exceeds_max_chars(self) -> None:
        chunker = LayoutAwareChunker(max_prose_chars=20)
        text = "A" * 30 + "\n\n" + "B" * 30
        result = chunker.chunk(doc(text))
        assert len(result) == 2
        assert all(r.metadata["chunk_type"] == "prose" for r in result)


# ---------------------------------------------------------------------------
# 2. Code block preservation
# ---------------------------------------------------------------------------

CODE_DOC = """\
Intro text.

```python
def add(a, b):
    return a + b
```

More prose after.
"""

class TestCodeBlockPreservation:
    def test_code_block_is_own_chunk(self) -> None:
        chunker = LayoutAwareChunker()
        chunks = chunker.chunk(doc(CODE_DOC))
        types = [c.metadata["chunk_type"] for c in chunks]
        assert "code" in types

    def test_code_block_content_preserved_verbatim(self) -> None:
        chunker = LayoutAwareChunker()
        chunks = chunker.chunk(doc(CODE_DOC))
        code_chunks = [c for c in chunks if c.metadata["chunk_type"] == "code"]
        assert len(code_chunks) == 1
        assert "def add(a, b):" in code_chunks[0].text
        assert "return a + b" in code_chunks[0].text

    def test_prose_before_code_separate_chunk(self) -> None:
        chunker = LayoutAwareChunker()
        chunks = chunker.chunk(doc(CODE_DOC))
        prose_chunks = [c for c in chunks if c.metadata["chunk_type"] == "prose"]
        assert any("Intro text" in c.text for c in prose_chunks)

    def test_tilde_fence_also_preserved(self) -> None:
        text = "pre\n\n~~~js\nconsole.log('hi');\n~~~\n\npost\n"
        chunker = LayoutAwareChunker()
        chunks = chunker.chunk(doc(text))
        code_chunks = [c for c in chunks if c.metadata["chunk_type"] == "code"]
        assert len(code_chunks) == 1
        assert "console.log" in code_chunks[0].text


# ---------------------------------------------------------------------------
# 3. Table preservation
# ---------------------------------------------------------------------------

TABLE_DOC = """\
Some intro.

| Col A | Col B |
|-------|-------|
| 1     | 2     |
| 3     | 4     |

Trailing prose.
"""

class TestTablePreservation:
    def test_table_is_own_chunk(self) -> None:
        chunker = LayoutAwareChunker()
        chunks = chunker.chunk(doc(TABLE_DOC))
        types = [c.metadata["chunk_type"] for c in chunks]
        assert "table" in types

    def test_table_content_intact(self) -> None:
        chunker = LayoutAwareChunker()
        chunks = chunker.chunk(doc(TABLE_DOC))
        table_chunks = [c for c in chunks if c.metadata["chunk_type"] == "table"]
        assert len(table_chunks) == 1
        assert "Col A" in table_chunks[0].text
        assert "Col B" in table_chunks[0].text
        assert "3" in table_chunks[0].text

    def test_table_not_split_by_max_chars(self) -> None:
        # Even with a tiny max, the table should stay whole.
        chunker = LayoutAwareChunker(max_prose_chars=10)
        chunks = chunker.chunk(doc(TABLE_DOC))
        table_chunks = [c for c in chunks if c.metadata["chunk_type"] == "table"]
        assert len(table_chunks) == 1


# ---------------------------------------------------------------------------
# 4. Math block preservation
# ---------------------------------------------------------------------------

MATH_DOC = """\
Einstein's formula:

$$
E = mc^2
$$

End of doc.
"""

class TestMathPreservation:
    def test_math_is_own_chunk(self) -> None:
        chunker = LayoutAwareChunker()
        chunks = chunker.chunk(doc(MATH_DOC))
        types = [c.metadata["chunk_type"] for c in chunks]
        assert "math" in types

    def test_math_content_intact(self) -> None:
        chunker = LayoutAwareChunker()
        chunks = chunker.chunk(doc(MATH_DOC))
        math_chunks = [c for c in chunks if c.metadata["chunk_type"] == "math"]
        assert len(math_chunks) == 1
        assert "E = mc^2" in math_chunks[0].text

    def test_math_not_split_by_max_chars(self) -> None:
        chunker = LayoutAwareChunker(max_prose_chars=5)
        chunks = chunker.chunk(doc(MATH_DOC))
        math_chunks = [c for c in chunks if c.metadata["chunk_type"] == "math"]
        assert len(math_chunks) == 1


# ---------------------------------------------------------------------------
# 5. Mixed document (prose + code + table + math)
# ---------------------------------------------------------------------------

MIXED_DOC = """\
Intro paragraph.

```sql
SELECT * FROM users;
```

| Name | Age |
|------|-----|
| Alice | 30 |

$$x^2 + y^2 = z^2$$

Final prose.
"""

class TestMixedDocument:
    def test_all_chunk_types_present(self) -> None:
        chunker = LayoutAwareChunker()
        chunks = chunker.chunk(doc(MIXED_DOC))
        types = {c.metadata["chunk_type"] for c in chunks}
        assert types == {"prose", "code", "table", "math"}

    def test_ordinals_are_sequential(self) -> None:
        chunker = LayoutAwareChunker()
        chunks = chunker.chunk(doc(MIXED_DOC))
        assert [c.ordinal for c in chunks] == list(range(len(chunks)))

    def test_all_chunks_have_document_id(self) -> None:
        chunker = LayoutAwareChunker()
        d = doc(MIXED_DOC)
        chunks = chunker.chunk(d)
        assert all(c.document_id == d.id for c in chunks)


# ---------------------------------------------------------------------------
# 6. Metadata fields
# ---------------------------------------------------------------------------

class TestMetadataFields:
    def test_chunk_has_source_field(self) -> None:
        d = Document(workspace_id=WS, title="t", text="hello world", source="page.md")
        chunker = LayoutAwareChunker()
        chunks = chunker.chunk(d)
        assert chunks[0].metadata["source"] == "page.md"

    def test_chunk_has_offset_fields(self) -> None:
        chunker = LayoutAwareChunker()
        chunks = chunker.chunk(doc("hello"))
        assert "offset_start" in chunks[0].metadata
        assert "offset_end" in chunks[0].metadata

    def test_constructor_rejects_nonpositive_max(self) -> None:
        with pytest.raises(ValueError):
            LayoutAwareChunker(max_prose_chars=0)
        with pytest.raises(ValueError):
            LayoutAwareChunker(max_prose_chars=-1)
