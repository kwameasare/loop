"""Tests for the Zep episodic adapter (S821)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID, uuid4

import pytest
from loop_memory.episodic import (
    EMBEDDING_DIM,
    EpisodicEntry,
    EpisodicStore,
    HashEmbedder,
)
from loop_memory.zep_adapter import ZepEpisodicStore, ZepError


def _entry(*, ws: UUID, agent: UUID, ts: int, summary: str) -> EpisodicEntry:
    embedder = HashEmbedder()
    return EpisodicEntry(
        id=uuid4(),
        workspace_id=ws,
        agent_id=agent,
        conversation_id=uuid4(),
        summary=summary,
        embedding=embedder.embed(summary),
        salience=0.5,
        ts_ms=ts,
    )


class FakeZep:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []
        self.add_calls: list[dict[str, Any]] = []
        self.search_args: list[dict[str, Any]] = []
        self.list_args: list[dict[str, Any]] = []

    async def add_episode(
        self,
        *,
        session_id: str,
        summary: str,
        metadata: dict[str, Any],
        embedding: Sequence[float],
    ) -> str:
        record = {
            "session_id": session_id,
            "summary": summary,
            "metadata": dict(metadata),
            "embedding": list(embedding),
        }
        self.records.append(record)
        self.add_calls.append({"session_id": session_id, "summary": summary})
        return str(metadata["loop_id"])

    async def search(
        self,
        *,
        session_id: str,
        embedding: Sequence[float],
        limit: int,
    ) -> list[dict[str, Any]]:
        self.search_args.append({"session_id": session_id, "limit": limit})
        return [
            {**record, "score": float(record.get("score", 0.9))}
            for record in self.records
            if record["session_id"] == session_id
        ][:limit]

    async def list_episodes(
        self,
        *,
        session_id: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        self.list_args.append({"session_id": session_id, "limit": limit})
        return [
            record for record in self.records if record["session_id"] == session_id
        ][:limit]


def test_satisfies_episodic_store_protocol() -> None:
    store = ZepEpisodicStore(client=FakeZep())
    assert isinstance(store, EpisodicStore)


@pytest.mark.asyncio
async def test_upsert_then_query_round_trip() -> None:
    ws, agent = uuid4(), uuid4()
    client = FakeZep()
    store = ZepEpisodicStore(client=client)
    e1 = _entry(ws=ws, agent=agent, ts=1_000, summary="customer asks about billing")
    e2 = _entry(ws=ws, agent=agent, ts=2_000, summary="agent explains refund policy")

    await store.upsert(e1)
    await store.upsert(e2)

    assert client.add_calls[0]["session_id"] == f"loop:{ws.hex}:{agent.hex}"
    results = await store.query(
        workspace_id=ws,
        agent_id=agent,
        embedding=e1.embedding,
        limit=5,
    )
    assert {entry.summary for entry, _score in results} == {
        "customer asks about billing",
        "agent explains refund policy",
    }


@pytest.mark.asyncio
async def test_query_min_score_filters() -> None:
    ws, agent = uuid4(), uuid4()
    client = FakeZep()
    store = ZepEpisodicStore(client=client)
    await store.upsert(_entry(ws=ws, agent=agent, ts=1, summary="low confidence"))
    client.records[0]["score"] = 0.25

    results = await store.query(
        workspace_id=ws,
        agent_id=agent,
        embedding=(0.0,) * EMBEDDING_DIM,
        limit=5,
        min_score=0.5,
    )

    assert results == []


@pytest.mark.asyncio
async def test_list_recent_orders_by_ts_desc() -> None:
    ws, agent = uuid4(), uuid4()
    client = FakeZep()
    store = ZepEpisodicStore(client=client)
    await store.upsert(_entry(ws=ws, agent=agent, ts=1_000, summary="old"))
    await store.upsert(_entry(ws=ws, agent=agent, ts=5_000, summary="new"))

    out = await store.list_recent(workspace_id=ws, agent_id=agent, limit=2)

    assert [entry.summary for entry in out] == ["new", "old"]


@pytest.mark.asyncio
async def test_query_rejects_bad_embedding_dim() -> None:
    ws, agent = uuid4(), uuid4()

    class BrokenClient(FakeZep):
        async def search(
            self,
            *,
            session_id: str,
            embedding: Sequence[float],
            limit: int,
        ) -> list[dict[str, Any]]:
            return [
                {
                    "summary": "bad vector",
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
                }
            ]

    store = ZepEpisodicStore(client=BrokenClient())
    with pytest.raises(ZepError):
        await store.query(
            workspace_id=ws,
            agent_id=agent,
            embedding=(0.0,) * EMBEDDING_DIM,
            limit=5,
        )


@pytest.mark.asyncio
async def test_upsert_wraps_client_failures() -> None:
    class BrokenClient(FakeZep):
        async def add_episode(
            self,
            *,
            session_id: str,
            summary: str,
            metadata: dict[str, Any],
            embedding: Sequence[float],
        ) -> str:
            raise RuntimeError("network down")

    store = ZepEpisodicStore(client=BrokenClient())
    with pytest.raises(ZepError):
        await store.upsert(_entry(ws=uuid4(), agent=uuid4(), ts=1, summary="x"))


@pytest.mark.asyncio
async def test_rejects_non_positive_limits() -> None:
    store = ZepEpisodicStore(client=FakeZep())
    with pytest.raises(ZepError):
        await store.query(
            workspace_id=uuid4(),
            agent_id=uuid4(),
            embedding=(0.0,) * EMBEDDING_DIM,
            limit=0,
        )
    with pytest.raises(ZepError):
        await store.list_recent(workspace_id=uuid4(), agent_id=uuid4(), limit=0)
