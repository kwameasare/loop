"""Tests for episodic memory (S035)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from loop_memory import (
    EMBEDDING_DIM,
    EpisodicEntry,
    EpisodicError,
    HashEmbedder,
    InMemoryEpisodicStore,
    auto_summarize,
    cosine_similarity,
)
from pydantic import ValidationError


def _entry(
    embedder: HashEmbedder,
    *,
    workspace_id,
    agent_id,
    text: str,
    salience: float = 0.5,
    ts_ms: int = 0,
) -> EpisodicEntry:
    return EpisodicEntry(
        workspace_id=workspace_id,
        agent_id=agent_id,
        conversation_id=uuid4(),
        summary=text,
        embedding=embedder.embed(text),
        salience=salience,
        ts_ms=ts_ms,
    )


def test_hash_embedder_is_deterministic_unit_length() -> None:
    e = HashEmbedder()
    a = e.embed("hello world")
    b = e.embed("hello world")
    c = e.embed("different")
    assert a == b
    assert a != c
    assert len(a) == EMBEDDING_DIM
    norm_sq = sum(x * x for x in a)
    assert abs(norm_sq - 1.0) < 1e-9


def test_cosine_self_is_one_and_orthogonal_is_zero() -> None:
    e = HashEmbedder()
    v = e.embed("anything")
    assert cosine_similarity(v, v) == pytest.approx(1.0)
    zero = (0.0,) * EMBEDDING_DIM
    assert cosine_similarity(v, zero) == 0.0


def test_cosine_rejects_length_mismatch() -> None:
    with pytest.raises(EpisodicError):
        cosine_similarity((1.0, 0.0), (1.0, 0.0, 0.0))


async def test_inmemory_store_query_ranks_by_similarity_then_salience() -> None:
    e = HashEmbedder()
    store = InMemoryEpisodicStore()
    ws, ag = uuid4(), uuid4()

    target = _entry(e, workspace_id=ws, agent_id=ag, text="customer asked about pricing")
    other = _entry(e, workspace_id=ws, agent_id=ag, text="weather is nice today")
    duplicate_text_high_salience = _entry(
        e,
        workspace_id=ws,
        agent_id=ag,
        text="customer asked about pricing",
        salience=0.9,
        ts_ms=10,
    )

    await store.upsert(target)
    await store.upsert(other)
    await store.upsert(duplicate_text_high_salience)

    query_vec = e.embed("customer asked about pricing")
    results = await store.query(workspace_id=ws, agent_id=ag, embedding=query_vec, limit=2)

    assert len(results) == 2
    # Both pricing entries score 1.0; tie-breaker = higher salience first.
    top, top_score = results[0]
    assert top_score == pytest.approx(1.0)
    assert top.salience == 0.9


async def test_inmemory_store_scopes_by_workspace_and_agent() -> None:
    e = HashEmbedder()
    store = InMemoryEpisodicStore()
    ws_a, ws_b, ag = uuid4(), uuid4(), uuid4()

    await store.upsert(_entry(e, workspace_id=ws_a, agent_id=ag, text="A"))
    await store.upsert(_entry(e, workspace_id=ws_b, agent_id=ag, text="B"))

    results = await store.query(
        workspace_id=ws_a, agent_id=ag, embedding=e.embed("A"), limit=5
    )
    assert len(results) == 1
    assert results[0][0].summary == "A"


async def test_inmemory_store_min_score_filter() -> None:
    e = HashEmbedder()
    store = InMemoryEpisodicStore()
    ws, ag = uuid4(), uuid4()
    await store.upsert(_entry(e, workspace_id=ws, agent_id=ag, text="hello"))

    # An unrelated query vector should drop below a high min_score.
    results = await store.query(
        workspace_id=ws,
        agent_id=ag,
        embedding=e.embed("totally unrelated text"),
        limit=5,
        min_score=0.99,
    )
    assert results == []


async def test_inmemory_store_list_recent_orders_by_ts_desc() -> None:
    e = HashEmbedder()
    store = InMemoryEpisodicStore()
    ws, ag = uuid4(), uuid4()

    await store.upsert(_entry(e, workspace_id=ws, agent_id=ag, text="first", ts_ms=1))
    await store.upsert(_entry(e, workspace_id=ws, agent_id=ag, text="third", ts_ms=3))
    await store.upsert(_entry(e, workspace_id=ws, agent_id=ag, text="second", ts_ms=2))

    recent = await store.list_recent(workspace_id=ws, agent_id=ag, limit=2)
    assert [r.summary for r in recent] == ["third", "second"]


async def test_inmemory_store_rejects_non_positive_limit() -> None:
    store = InMemoryEpisodicStore()
    ws, ag = uuid4(), uuid4()
    with pytest.raises(EpisodicError):
        await store.query(
            workspace_id=ws, agent_id=ag, embedding=(0.0,) * EMBEDDING_DIM, limit=0
        )
    with pytest.raises(EpisodicError):
        await store.list_recent(workspace_id=ws, agent_id=ag, limit=0)


def test_episodic_entry_validates_salience_and_embedding_dim() -> None:
    e = HashEmbedder()
    with pytest.raises(ValidationError):
        EpisodicEntry(
            workspace_id=uuid4(),
            agent_id=uuid4(),
            conversation_id=uuid4(),
            summary="x",
            embedding=e.embed("x"),
            salience=1.5,  # > 1
            ts_ms=0,
        )
    with pytest.raises(ValidationError):
        EpisodicEntry(
            workspace_id=uuid4(),
            agent_id=uuid4(),
            conversation_id=uuid4(),
            summary="x",
            embedding=(0.1, 0.2),  # wrong dim
            salience=0.5,
            ts_ms=0,
        )


def test_auto_summarize_joins_and_truncates() -> None:
    summary = auto_summarize(["hello", "world", "  ", "again"])
    assert summary == "hello | world | again"

    long_msgs = ["aaaa " * 100, "bbbb " * 100]
    short = auto_summarize(long_msgs, max_chars=20)
    assert len(short) == 20
    assert short.endswith("\u2026")


def test_auto_summarize_rejects_empty_input_and_bad_max_chars() -> None:
    with pytest.raises(EpisodicError):
        auto_summarize([])
    with pytest.raises(EpisodicError):
        auto_summarize(["", "   "])
    with pytest.raises(EpisodicError):
        auto_summarize(["hi"], max_chars=0)
