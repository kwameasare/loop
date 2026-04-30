"""Tests for pass10 mem0 adapter (S820)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from loop_memory.episodic import (
    EMBEDDING_DIM,
    EpisodicEntry,
    EpisodicStore,
    HashEmbedder,
)
from loop_memory.mem0_adapter import Mem0EpisodicStore, Mem0Error


def _entry(*, ws, agent, ts: int, summary: str, salience: float = 0.5) -> EpisodicEntry:
    embedder = HashEmbedder()
    vec = embedder.embed(summary)
    return EpisodicEntry(
        id=uuid4(),
        workspace_id=ws,
        agent_id=agent,
        conversation_id=uuid4(),
        summary=summary,
        embedding=vec,
        salience=salience,
        ts_ms=ts,
    )


class FakeMem0:
    def __init__(self):
        self.records: list[dict] = []
        self.add_calls: list[dict] = []
        self.search_args: list[dict] = []
        self.list_args: list[dict] = []

    async def add(self, *, user_id, memory, metadata, embedding) -> str:
        rec = {
            "memory": memory,
            "metadata": dict(metadata),
            "embedding": list(embedding),
            "user_id": user_id,
        }
        self.records.append(rec)
        self.add_calls.append({"user_id": user_id, "memory": memory})
        return rec["metadata"]["loop_id"]

    async def search(self, *, user_id, embedding, limit):
        self.search_args.append({"user_id": user_id, "limit": limit})
        return [
            {**r, "score": 0.9} for r in self.records if r["user_id"] == user_id
        ][:limit]

    async def list(self, *, user_id, limit):
        self.list_args.append({"user_id": user_id, "limit": limit})
        return [r for r in self.records if r["user_id"] == user_id][:limit]


def test_satisfies_episodic_store_protocol():
    store = Mem0EpisodicStore(client=FakeMem0())
    assert isinstance(store, EpisodicStore)


@pytest.mark.asyncio
async def test_upsert_then_query_round_trip():
    ws, agent = uuid4(), uuid4()
    client = FakeMem0()
    store = Mem0EpisodicStore(client=client)
    e1 = _entry(ws=ws, agent=agent, ts=1_000, summary="hello world")
    e2 = _entry(ws=ws, agent=agent, ts=2_000, summary="goodbye")
    await store.upsert(e1)
    await store.upsert(e2)
    assert client.add_calls and "loop:" in client.add_calls[0]["user_id"]
    results = await store.query(
        workspace_id=ws, agent_id=agent, embedding=e1.embedding, limit=5
    )
    assert len(results) == 2
    summaries = {entry.summary for entry, _score in results}
    assert summaries == {"hello world", "goodbye"}


@pytest.mark.asyncio
async def test_query_min_score_filters():
    ws, agent = uuid4(), uuid4()
    client = FakeMem0()
    store = Mem0EpisodicStore(client=client)
    await store.upsert(_entry(ws=ws, agent=agent, ts=1, summary="x"))
    # min_score above the constant fake score 0.9 → no results
    results = await store.query(
        workspace_id=ws, agent_id=agent, embedding=(0.0,) * EMBEDDING_DIM,
        limit=5, min_score=0.99,
    )
    assert results == []


@pytest.mark.asyncio
async def test_list_recent_orders_by_ts_desc():
    ws, agent = uuid4(), uuid4()
    client = FakeMem0()
    store = Mem0EpisodicStore(client=client)
    e_old = _entry(ws=ws, agent=agent, ts=1_000, summary="old")
    e_new = _entry(ws=ws, agent=agent, ts=5_000, summary="new")
    await store.upsert(e_old)
    await store.upsert(e_new)
    out = await store.list_recent(workspace_id=ws, agent_id=agent, limit=2)
    assert [e.summary for e in out] == ["new", "old"]


@pytest.mark.asyncio
async def test_query_rejects_bad_embedding_dim():
    ws, agent = uuid4(), uuid4()

    class BrokenClient:
        async def add(self, **kwargs):
            return "x"

        async def search(self, *, user_id, embedding, limit):
            # Return a record with wrong-dim embedding.
            return [{
                "memory": "summary",
                "metadata": {
                    "loop_id": str(uuid4()),
                    "workspace_id": str(ws),
                    "agent_id": str(agent),
                    "conversation_id": str(uuid4()),
                    "salience": 0.5,
                    "ts_ms": 1,
                },
                "embedding": [0.0, 0.0, 0.0],
                "score": 0.5,
            }]

        async def list(self, *, user_id, limit):
            return []

    store = Mem0EpisodicStore(client=BrokenClient())
    with pytest.raises(Mem0Error):
        await store.query(
            workspace_id=ws,
            agent_id=agent,
            embedding=(0.0,) * EMBEDDING_DIM,
            limit=5,
        )


@pytest.mark.asyncio
async def test_upsert_wraps_client_failures():
    class BrokenClient:
        async def add(self, **kwargs):
            raise RuntimeError("network down")

        async def search(self, **kwargs):
            return []

        async def list(self, **kwargs):
            return []

    store = Mem0EpisodicStore(client=BrokenClient())
    e = _entry(ws=uuid4(), agent=uuid4(), ts=1, summary="x")
    with pytest.raises(Mem0Error):
        await store.upsert(e)


@pytest.mark.asyncio
async def test_query_rejects_non_positive_limit():
    store = Mem0EpisodicStore(client=FakeMem0())
    with pytest.raises(Mem0Error):
        await store.query(
            workspace_id=uuid4(),
            agent_id=uuid4(),
            embedding=(0.0,) * EMBEDDING_DIM,
            limit=0,
        )


@pytest.mark.asyncio
async def test_list_recent_rejects_non_positive_limit():
    store = Mem0EpisodicStore(client=FakeMem0())
    with pytest.raises(Mem0Error):
        await store.list_recent(workspace_id=uuid4(), agent_id=uuid4(), limit=0)
