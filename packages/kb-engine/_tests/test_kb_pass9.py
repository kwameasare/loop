"""Pass9 tests for kb-engine: PDF/HTML/DOCX parsers + voyage/bge embedders + reranker + episodic config."""

from __future__ import annotations

from uuid import uuid4

import pytest
from loop_kb_engine.embeddings_bge import (
    MODEL_DIMENSIONS as BGE_DIMS,
)
from loop_kb_engine.embeddings_bge import (
    BgeLocalEmbeddingService,
    EncoderDimensionError,
)
from loop_kb_engine.embeddings_voyage import (
    MODEL_DIMENSIONS as VOYAGE_DIMS,
)
from loop_kb_engine.embeddings_voyage import (
    EmbeddingProviderError,
    VoyageEmbeddingService,
)
from loop_kb_engine.episodic import (
    EpisodicCollectionConfig,
    collection_name,
)
from loop_kb_engine.parsers import DocumentParseError
from loop_kb_engine.parsers_docx import (
    DocxBlockKind,
    DocxHeading,
    DocxParagraph,
    DocxParser,
    DocxTable,
    render_blocks,
)
from loop_kb_engine.parsers_html import HtmlParser
from loop_kb_engine.parsers_pdf import PAGE_MARKER_TEMPLATE, PdfPage, PdfParser, join_pages
from loop_kb_engine.reranker import (
    CohereReranker,
    LexicalOverlapReranker,
    RerankError,
    RerankHit,
)

WS = uuid4()


# --- PDF -----------------------------------------------------------------


def test_pdf_join_pages_uses_marker():
    pages = (PdfPage(page_no=1, text="hello"), PdfPage(page_no=2, text="world"))
    out = join_pages(pages)
    assert "page 1" in out and "page 2" in out
    assert "hello" in out and "world" in out


def test_pdf_parse_pages_records_metadata():
    parser = PdfParser()
    pages = (PdfPage(page_no=1, text="a"), PdfPage(page_no=3, text="c"))  # gap allowed
    doc = parser.parse_pages(pages, workspace_id=WS, title="t", source="x.pdf")
    assert doc.metadata["page_count"] == "2"
    assert doc.source == "x.pdf"


def test_pdf_parse_rejects_duplicate_page_no():
    parser = PdfParser()
    with pytest.raises(DocumentParseError):
        parser.parse_pages(
            (PdfPage(page_no=1, text="a"), PdfPage(page_no=1, text="b")),
            workspace_id=WS,
            title="t",
        )


def test_pdf_parse_rejects_non_increasing():
    parser = PdfParser()
    with pytest.raises(DocumentParseError):
        parser.parse_pages(
            (PdfPage(page_no=2, text="a"), PdfPage(page_no=1, text="b")),
            workspace_id=WS,
            title="t",
        )


def test_pdf_parse_empty_bytes_raises():
    with pytest.raises(DocumentParseError):
        PdfParser().parse(b"", workspace_id=WS, title="t")


def test_pdf_page_validates_page_no():
    with pytest.raises(ValueError):
        PdfPage(page_no=0, text="x")


def test_pdf_marker_includes_page_number():
    assert PAGE_MARKER_TEMPLATE.format(page_no=42).strip() == "--- page 42 ---"


# --- HTML ----------------------------------------------------------------


def test_html_strips_nav_and_script():
    raw = "<html><body><nav>menu</nav><p>hello</p><script>alert(1)</script></body></html>"
    doc = HtmlParser().parse_text(raw, workspace_id=WS, title="t")
    assert "hello" in doc.text
    assert "menu" not in doc.text
    assert "alert" not in doc.text


def test_html_preserves_headings_as_markdown():
    raw = "<html><body><h2>Topic</h2><p>body</p></body></html>"
    doc = HtmlParser().parse_text(raw, workspace_id=WS, title="t")
    assert "## Topic" in doc.text


def test_html_main_tag_filters_to_content():
    raw = "<html><body><nav>nav-text</nav><main><p>main-content</p></main><footer>foot</footer></body></html>"
    doc = HtmlParser().parse_text(raw, workspace_id=WS, title="t")
    assert "main-content" in doc.text
    assert "nav-text" not in doc.text
    assert "foot" not in doc.text


def test_html_captures_title_metadata():
    raw = "<html><head><title>The Title</title></head><body><p>x</p></body></html>"
    doc = HtmlParser().parse_text(raw, workspace_id=WS, title="t")
    assert doc.metadata["html_title"] == "The Title"


def test_html_rejects_invalid_utf8():
    with pytest.raises(DocumentParseError):
        HtmlParser().parse(b"\xff\xfe<bad>", workspace_id=WS, title="t")


def test_html_parses_5_fixtures():
    fixtures = [
        ("<p>simple</p>", "simple"),
        ("<article><p>hello</p></article>", "hello"),
        ("<div>x</div><div>y</div>", "x"),
        ("<h1>H</h1><p>body</p>", "# H"),
        ("<ul><li>a</li><li>b</li></ul>", "a"),
    ]
    for raw, must_contain in fixtures:
        doc = HtmlParser().parse_text(raw, workspace_id=WS, title="t")
        assert must_contain in doc.text


# --- DOCX ----------------------------------------------------------------


def test_docx_render_blocks_emits_markdown_table():
    blocks: tuple = (
        DocxHeading(level=1, text="Title"),
        DocxParagraph(text="prose"),
        DocxTable(rows=(("a", "b"), ("1", "2"))),
    )
    out = render_blocks(blocks)
    assert "# Title" in out
    assert "| a | b |" in out
    assert "| --- | --- |" in out
    assert "| 1 | 2 |" in out


def test_docx_table_must_be_rectangular():
    with pytest.raises(ValueError):
        DocxTable(rows=(("a", "b"), ("c",)))


def test_docx_heading_level_validation():
    with pytest.raises(ValueError):
        DocxHeading(level=7, text="x")


def test_docx_parser_metadata_counts():
    parser = DocxParser(backend=_FakeDocxBackend())
    doc = parser.parse(b"x", workspace_id=WS, title="t")
    assert doc.metadata["heading_count"] == "1"
    assert doc.metadata["table_count"] == "1"
    assert doc.metadata["block_count"] == "3"


class _FakeDocxBackend:
    def extract(self, data):
        return (
            DocxHeading(level=1, text="H"),
            DocxParagraph(text="P"),
            DocxTable(rows=(("a",), ("b",))),
        )


def test_docx_parse_empty_bytes_raises():
    with pytest.raises(DocumentParseError):
        DocxParser().parse(b"", workspace_id=WS, title="t")


def test_docx_block_kind_enum():
    assert DocxBlockKind.HEADING.value == "heading"


# --- Voyage embedder -----------------------------------------------------


class _FakeHttp:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self.payload = payload
        self.calls: list[dict] = []

    async def post_json(self, url, *, headers, body):
        self.calls.append({"url": url, "headers": headers, "body": body})
        return self.status, self.payload


@pytest.mark.asyncio
async def test_voyage_embed_happy_path():
    payload = {"data": [{"embedding": [0.1] * VOYAGE_DIMS["voyage-3"]}]}
    http = _FakeHttp(200, payload)
    svc = VoyageEmbeddingService(api_key="k", http=http)
    out = await svc.embed(["hello"])
    assert len(out) == 1
    assert len(out[0]) == svc.dimensions
    assert http.calls[0]["body"]["model"] == "voyage-3"


@pytest.mark.asyncio
async def test_voyage_rejects_dim_mismatch():
    http = _FakeHttp(200, {"data": [{"embedding": [0.1, 0.2]}]})
    svc = VoyageEmbeddingService(api_key="k", http=http)
    with pytest.raises(EmbeddingProviderError):
        await svc.embed(["x"])


@pytest.mark.asyncio
async def test_voyage_propagates_non_2xx():
    http = _FakeHttp(500, {"err": "boom"})
    svc = VoyageEmbeddingService(api_key="k", http=http)
    with pytest.raises(EmbeddingProviderError):
        await svc.embed(["x"])


@pytest.mark.asyncio
async def test_voyage_empty_input_short_circuits():
    http = _FakeHttp(200, {})
    svc = VoyageEmbeddingService(api_key="k", http=http)
    assert await svc.embed([]) == []
    assert http.calls == []


def test_voyage_rejects_unknown_model():
    with pytest.raises(ValueError):
        VoyageEmbeddingService(api_key="k", http=_FakeHttp(200, {}), model="bogus")


def test_voyage_rejects_empty_key():
    with pytest.raises(ValueError):
        VoyageEmbeddingService(api_key="", http=_FakeHttp(200, {}))


# --- BGE embedder --------------------------------------------------------


class _FakeEncoder:
    def __init__(self, dim: int):
        self.dim = dim

    def encode(self, texts):
        return [[0.5] * self.dim for _ in texts]


@pytest.mark.asyncio
async def test_bge_embed_dimensions_match_card():
    enc = _FakeEncoder(BGE_DIMS["BAAI/bge-large-en-v1.5"])
    svc = BgeLocalEmbeddingService(encoder=enc)
    out = await svc.embed(["a", "b"])
    assert len(out) == 2
    assert all(len(v) == svc.dimensions for v in out)


@pytest.mark.asyncio
async def test_bge_dim_mismatch_raises():
    enc = _FakeEncoder(7)
    svc = BgeLocalEmbeddingService(encoder=enc)
    with pytest.raises(EncoderDimensionError):
        await svc.embed(["a"])


@pytest.mark.asyncio
async def test_bge_empty_short_circuits():
    enc = _FakeEncoder(BGE_DIMS["BAAI/bge-large-en-v1.5"])
    svc = BgeLocalEmbeddingService(encoder=enc)
    assert await svc.embed([]) == []


def test_bge_rejects_unknown_model():
    with pytest.raises(ValueError):
        BgeLocalEmbeddingService(encoder=_FakeEncoder(1), model="bogus")


# --- Reranker ------------------------------------------------------------


@pytest.mark.asyncio
async def test_lexical_reranker_orders_by_overlap():
    hits = [
        RerankHit(id="a", text="completely unrelated thing"),
        RerankHit(id="b", text="the answer is forty two indeed"),
        RerankHit(id="c", text="forty two is the answer"),
    ]
    out = await LexicalOverlapReranker().rerank("the answer forty two", hits)
    assert out[0].id in {"b", "c"}
    assert out[-1].id == "a"


@pytest.mark.asyncio
async def test_lexical_reranker_top_n_clip():
    hits = [RerankHit(id=str(i), text="x") for i in range(5)]
    out = await LexicalOverlapReranker().rerank("x", hits, top_n=2)
    assert len(out) == 2


@pytest.mark.asyncio
async def test_cohere_reranker_remaps_indices():
    payload = {
        "results": [
            {"index": 1, "relevance_score": 0.9},
            {"index": 0, "relevance_score": 0.1},
        ]
    }
    http = _FakeHttp(200, payload)
    rr = CohereReranker(api_key="k", http=http)
    hits = [RerankHit(id="a", text="x"), RerankHit(id="b", text="y")]
    out = await rr.rerank("q", hits)
    assert [h.id for h in out] == ["b", "a"]
    assert out[0].score == 0.9


@pytest.mark.asyncio
async def test_cohere_propagates_error():
    http = _FakeHttp(429, {"err": "rate limited"})
    rr = CohereReranker(api_key="k", http=http)
    with pytest.raises(RerankError):
        await rr.rerank("q", [RerankHit(id="a", text="x")])


@pytest.mark.asyncio
async def test_cohere_rejects_out_of_range_index():
    payload = {"results": [{"index": 99, "relevance_score": 0.5}]}
    rr = CohereReranker(api_key="k", http=_FakeHttp(200, payload))
    with pytest.raises(RerankError):
        await rr.rerank("q", [RerankHit(id="a", text="x")])


# --- Episodic collection -------------------------------------------------


def test_episodic_collection_name_validation():
    assert collection_name("agent-42") == "episodic_agent-42"
    with pytest.raises(ValueError):
        collection_name("Bad Name")
    with pytest.raises(ValueError):
        collection_name("")


def test_episodic_config_payload():
    cfg = EpisodicCollectionConfig(agent_id="support-bot", dimensions=1024)
    body = cfg.to_create_payload()
    assert body["vectors"]["size"] == 1024
    assert body["vectors"]["distance"] == "Cosine"
    assert cfg.collection_name == "episodic_support-bot"


def test_episodic_config_rejects_bad_distance():
    with pytest.raises(ValueError):
        EpisodicCollectionConfig(agent_id="a", distance="Manhattan")
