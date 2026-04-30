"""Tests for pass4 kb-engine substance: S210 ingest events, S207 list_documents."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from loop_kb_engine.chunker import SemanticChunker
from loop_kb_engine.embeddings import DeterministicEmbeddingService
from loop_kb_engine.ingest_events import (
    IngestEvent,
    IngestEventBus,
    ProgressSink,
)
from loop_kb_engine.kb import KnowledgeBase
from loop_kb_engine.models import Document
from loop_kb_engine.store import InMemoryVectorStore


# --------------------------------------------------------------- S210 events
@pytest.mark.asyncio
async def test_event_bus_fans_out_to_subscribers() -> None:
    bus = IngestEventBus()
    received_a: list[IngestEvent] = []
    received_b: list[IngestEvent] = []

    async def consume(target: list[IngestEvent], n: int) -> None:
        async for event in bus.subscribe():
            target.append(event)
            if len(target) == n:
                return

    task_a = asyncio.create_task(consume(received_a, 1))
    task_b = asyncio.create_task(consume(received_b, 1))
    # Give subscribers a moment to register before publishing.
    for _ in range(10):
        if bus.subscriber_count == 2:
            break
        await asyncio.sleep(0.01)
    assert bus.subscriber_count == 2

    ws = uuid4()
    doc = uuid4()
    await bus.publish(
        IngestEvent(workspace_id=ws, document_id=doc, kind="document.received")
    )
    await asyncio.gather(task_a, task_b)
    assert received_a[0].document_id == doc
    assert received_b[0].document_id == doc


@pytest.mark.asyncio
async def test_event_bus_forwards_to_external_sink() -> None:
    received: list[IngestEvent] = []

    class CollectingSink:
        async def emit(self, event: IngestEvent) -> None:
            received.append(event)

    sink = CollectingSink()
    assert isinstance(sink, ProgressSink)
    bus = IngestEventBus(sink=sink)
    ws, doc = uuid4(), uuid4()
    await bus.publish(
        IngestEvent(
            workspace_id=ws, document_id=doc, kind="document.indexed",
            chunks_total=4, chunks_done=4,
        )
    )
    assert len(received) == 1
    assert received[0].kind == "document.indexed"


@pytest.mark.asyncio
async def test_event_bus_validates_event_shape() -> None:
    with pytest.raises(ValueError):
        IngestEvent(
            workspace_id=uuid4(),
            document_id=uuid4(),
            kind="document.received",
            chunks_done=-1,  # type: ignore[arg-type]
        )


# --------------------------------------------------------------- S207 list
def _make_kb() -> KnowledgeBase:
    return KnowledgeBase(
        chunker=SemanticChunker(),
        embedder=DeterministicEmbeddingService(),
        vector_store=InMemoryVectorStore(),
    )


@pytest.mark.asyncio
async def test_kb_list_documents_returns_distinct_ids_after_ingest() -> None:
    kb = _make_kb()
    ws = uuid4()
    doc_a = Document(
        id=uuid4(), workspace_id=ws, title="a",
        text="alpha bravo charlie delta echo foxtrot",
    )
    doc_b = Document(
        id=uuid4(), workspace_id=ws, title="b",
        text="golf hotel india juliet kilo lima",
    )
    await kb.ingest(doc_a)
    await kb.ingest(doc_b)
    ids = await kb.list_documents(workspace_id=ws)
    assert set(ids) == {doc_a.id, doc_b.id}


@pytest.mark.asyncio
async def test_kb_list_documents_excludes_deleted() -> None:
    kb = _make_kb()
    ws = uuid4()
    doc = Document(
        id=uuid4(), workspace_id=ws, title="a",
        text="hello world from the kb engine",
    )
    await kb.ingest(doc)
    await kb.delete_document(workspace_id=ws, document_id=doc.id)
    assert await kb.list_documents(workspace_id=ws) == ()
