from __future__ import annotations

from uuid import uuid4

import pytest
from loop_kb_engine import (
    DeterministicEmbeddingService,
    Document,
    FixedSizeChunker,
    InMemoryVectorStore,
    KnowledgeBase,
    SemanticChunker,
)


def _doc(text: str, *, ws: object | None = None) -> Document:
    return Document(
        workspace_id=ws or uuid4(),
        title="t",
        text=text,
    )


def test_fixed_size_chunker_overlap_and_count() -> None:
    doc = _doc("a" * 1000)
    chunker = FixedSizeChunker(chunk_size=300, overlap=50)
    chunks = chunker.chunk(doc)
    # First chunk is 0..300, step = 250, so chunks start at 0, 250, 500, 750,
    # producing 4 windows.
    assert len(chunks) == 4
    assert all(c.workspace_id == doc.workspace_id for c in chunks)
    assert [c.ordinal for c in chunks] == [0, 1, 2, 3]


def test_fixed_size_chunker_validates() -> None:
    with pytest.raises(ValueError):
        FixedSizeChunker(chunk_size=0)
    with pytest.raises(ValueError):
        FixedSizeChunker(chunk_size=100, overlap=100)


def test_semantic_chunker_merges_paragraphs() -> None:
    text = "alpha line.\n\nbeta line.\n\n" + ("gamma " * 200)
    doc = _doc(text)
    chunks = SemanticChunker(max_chars=200).chunk(doc)
    # alpha+beta merge into one chunk under 200 chars; the gamma block
    # blows past max_chars and lands on its own.
    assert len(chunks) == 2
    assert "alpha" in chunks[0].text and "beta" in chunks[0].text
    assert "gamma" in chunks[1].text


@pytest.mark.asyncio
async def test_ingest_and_retrieve_dense_only() -> None:
    ws = uuid4()
    kb = KnowledgeBase(
        embedder=DeterministicEmbeddingService(dimensions=32),
        vector_store=InMemoryVectorStore(),
    )
    await kb.ingest(_doc("the cat sat on the mat", ws=ws))
    await kb.ingest(_doc("python is a programming language", ws=ws))

    results = await kb.retrieve(workspace_id=ws, query="cat sat on mat", alpha=0.0)
    assert results
    assert "cat" in results[0].chunk.text


@pytest.mark.asyncio
async def test_retrieve_bm25_finds_lexical_match() -> None:
    ws = uuid4()
    kb = KnowledgeBase(
        embedder=DeterministicEmbeddingService(dimensions=32),
        vector_store=InMemoryVectorStore(),
    )
    await kb.ingest(_doc("kubernetes orchestrates containers", ws=ws))
    await kb.ingest(_doc("postgres is a relational database", ws=ws))
    await kb.ingest(_doc("redis is a key value store", ws=ws))

    results = await kb.retrieve(workspace_id=ws, query="kubernetes", alpha=1.0)
    assert results
    assert "kubernetes" in results[0].chunk.text
    assert results[0].bm25_score > 0


@pytest.mark.asyncio
async def test_hybrid_blends_signals() -> None:
    ws = uuid4()
    kb = KnowledgeBase(
        embedder=DeterministicEmbeddingService(dimensions=32),
        vector_store=InMemoryVectorStore(),
    )
    await kb.ingest(_doc("kubernetes orchestrates containers in production", ws=ws))
    await kb.ingest(_doc("the bunny eats carrots in the garden", ws=ws))

    res = await kb.retrieve(workspace_id=ws, query="kubernetes containers", top_k=2, alpha=0.5)
    assert res[0].score >= res[-1].score
    assert "kubernetes" in res[0].chunk.text


@pytest.mark.asyncio
async def test_workspace_isolation() -> None:
    ws_a, ws_b = uuid4(), uuid4()
    kb = KnowledgeBase(
        embedder=DeterministicEmbeddingService(dimensions=32),
        vector_store=InMemoryVectorStore(),
    )
    await kb.ingest(_doc("alpha tenant secret", ws=ws_a))
    await kb.ingest(_doc("beta tenant secret", ws=ws_b))

    res_a = await kb.retrieve(workspace_id=ws_a, query="secret", top_k=5, alpha=0.5)
    assert res_a
    assert all("alpha" in r.chunk.text for r in res_a)


@pytest.mark.asyncio
async def test_delete_document_removes_from_both_indexes() -> None:
    ws = uuid4()
    kb = KnowledgeBase(
        embedder=DeterministicEmbeddingService(dimensions=32),
        vector_store=InMemoryVectorStore(),
    )
    doc = _doc("removable content here", ws=ws)
    chunks = await kb.ingest(doc)
    assert chunks

    removed = await kb.delete_document(workspace_id=ws, document_id=doc.id)
    assert removed >= 1

    # No more lexical or dense hits.
    res = await kb.retrieve(workspace_id=ws, query="removable", top_k=3, alpha=0.5)
    assert res == []


@pytest.mark.asyncio
async def test_alpha_validated() -> None:
    kb = KnowledgeBase(
        embedder=DeterministicEmbeddingService(dimensions=32),
        vector_store=InMemoryVectorStore(),
    )
    with pytest.raises(ValueError):
        await kb.retrieve(workspace_id=uuid4(), query="x", alpha=1.5)


@pytest.mark.asyncio
async def test_deterministic_embedder_stable_and_normalised() -> None:
    e = DeterministicEmbeddingService(dimensions=16)
    a = (await e.embed(["hello"]))[0]
    b = (await e.embed(["hello"]))[0]
    assert a == b
    # L2 norm ~ 1
    norm = sum(x * x for x in a) ** 0.5
    assert abs(norm - 1.0) < 1e-9
