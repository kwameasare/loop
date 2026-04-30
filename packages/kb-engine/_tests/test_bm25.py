"""Pass6 BM25 sparse-search tests."""

from __future__ import annotations

from loop_kb_engine.bm25 import BM25Index, tokenise


def test_tokenise_basic() -> None:
    assert tokenise("Hello, World! 2026") == ["hello", "world", "2026"]


def test_bm25_ranks_by_term_frequency() -> None:
    idx = BM25Index()
    idx.upsert(
        workspace_id="w",
        agent_id="a",
        chunk_id="c1",
        text="the quick brown fox jumps over the lazy dog",
    )
    idx.upsert(
        workspace_id="w",
        agent_id="a",
        chunk_id="c2",
        text="dogs and foxes are different but both run fast",
    )
    idx.upsert(
        workspace_id="w",
        agent_id="a",
        chunk_id="c3",
        text="completely unrelated content about banking software",
    )
    hits = idx.search(workspace_id="w", agent_id="a", query="lazy dog", top_k=3)
    assert hits[0].chunk_id == "c1"
    assert hits[0].score > 0
    assert all(h.chunk_id != "c3" for h in hits)


def test_bm25_workspace_isolation() -> None:
    idx = BM25Index()
    idx.upsert(workspace_id="w1", agent_id="a", chunk_id="c1", text="hello world")
    idx.upsert(workspace_id="w2", agent_id="a", chunk_id="c1", text="goodbye world")
    h1 = idx.search(workspace_id="w1", agent_id="a", query="hello")
    h2 = idx.search(workspace_id="w2", agent_id="a", query="hello")
    assert h1 and h1[0].chunk_id == "c1"
    assert not h2  # 'hello' missing from w2 shard


def test_bm25_upsert_replaces_existing() -> None:
    idx = BM25Index()
    idx.upsert(workspace_id="w", agent_id="a", chunk_id="c1", text="alpha alpha alpha")
    idx.upsert(workspace_id="w", agent_id="a", chunk_id="c1", text="zebra zebra")
    hits = idx.search(workspace_id="w", agent_id="a", query="alpha")
    assert hits == []
    hits2 = idx.search(workspace_id="w", agent_id="a", query="zebra")
    assert hits2 and hits2[0].chunk_id == "c1"


def test_bm25_score_threshold_filters() -> None:
    idx = BM25Index()
    for i, text in enumerate(["machine learning model", "model machine", "weather"]):
        idx.upsert(
            workspace_id="w", agent_id="a", chunk_id=f"c{i}", text=text
        )
    all_hits = idx.search(
        workspace_id="w", agent_id="a", query="machine", top_k=10
    )
    threshold = max(h.score for h in all_hits) - 0.001
    filtered = idx.search(
        workspace_id="w",
        agent_id="a",
        query="machine",
        top_k=10,
        score_threshold=threshold,
    )
    assert len(filtered) < len(all_hits)


def test_bm25_remove_chunk() -> None:
    idx = BM25Index()
    idx.upsert(workspace_id="w", agent_id="a", chunk_id="c1", text="apple banana")
    idx.upsert(workspace_id="w", agent_id="a", chunk_id="c2", text="apple cherry")
    idx.remove(workspace_id="w", agent_id="a", chunk_id="c1")
    hits = idx.search(workspace_id="w", agent_id="a", query="apple")
    assert [h.chunk_id for h in hits] == ["c2"]


def test_bm25_metadata_passed_through() -> None:
    idx = BM25Index()
    idx.upsert(
        workspace_id="w",
        agent_id="a",
        chunk_id="c1",
        text="hello world",
        metadata={"source": "doc-42", "lang": "en"},
    )
    hits = idx.search(workspace_id="w", agent_id="a", query="hello")
    assert hits[0].metadata["source"] == "doc-42"
