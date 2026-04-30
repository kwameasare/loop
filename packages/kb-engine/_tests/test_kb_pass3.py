"""Tests for pass3 substance: EmbeddingVector, RRF, tombstones, hash-diff."""

from __future__ import annotations

import math
from uuid import uuid4

import pytest
from loop_kb_engine import (
    Chunk,
    ChunkDiff,
    EmbeddingVector,
    TombstoneRegistry,
    chunk_content_hash,
    diff_chunks,
    rrf_combine,
)

# ---------------------------------------------------------------------------
# S190: EmbeddingVector
# ---------------------------------------------------------------------------


def _chunk(*, text: str = "hi") -> Chunk:
    return Chunk(
        document_id=uuid4(),
        workspace_id=uuid4(),
        ordinal=0,
        text=text,
    )


def test_embedding_vector_round_trip() -> None:
    chunk = _chunk()
    vec = EmbeddingVector.of(chunk=chunk, model="text-embedding-3-large", values=[0.1, 0.2, 0.3])
    dumped = vec.model_dump()
    restored = EmbeddingVector.model_validate(dumped)
    assert restored == vec
    assert restored.dim == 3


def test_embedding_vector_rejects_nan() -> None:
    chunk = _chunk()
    with pytest.raises(ValueError, match="finite"):
        EmbeddingVector.of(chunk=chunk, model="m", values=[0.1, math.nan])


def test_embedding_vector_rejects_inf() -> None:
    chunk = _chunk()
    with pytest.raises(ValueError, match="finite"):
        EmbeddingVector.of(chunk=chunk, model="m", values=[math.inf, 0.0])


def test_embedding_vector_rejects_empty_values() -> None:
    chunk = _chunk()
    with pytest.raises(Exception):  # noqa: B017 -- pydantic ValidationError
        EmbeddingVector(
            chunk_id=chunk.id,
            workspace_id=chunk.workspace_id,
            model="m",
            values=(),
        )


def test_embedding_vector_rejects_blank_model() -> None:
    chunk = _chunk()
    with pytest.raises(Exception):  # noqa: B017
        EmbeddingVector.of(chunk=chunk, model="", values=[0.1])


def test_embedding_vector_is_frozen() -> None:
    chunk = _chunk()
    vec = EmbeddingVector.of(chunk=chunk, model="m", values=[0.1])
    with pytest.raises(Exception):  # noqa: B017 -- frozen model
        vec.model = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# S205: RRF combiner
# ---------------------------------------------------------------------------


def test_rrf_fuses_two_rankings() -> None:
    ws = uuid4()
    a = Chunk(document_id=uuid4(), workspace_id=ws, ordinal=0, text="a")
    b = Chunk(document_id=uuid4(), workspace_id=ws, ordinal=1, text="b")
    c = Chunk(document_id=uuid4(), workspace_id=ws, ordinal=2, text="c")

    vec = [(a, 0.9), (b, 0.5), (c, 0.1)]
    bm25 = [(b, 7.0), (a, 5.0), (c, 1.0)]

    fused = rrf_combine([vec, bm25], k=60)
    ids = [chunk.id for chunk, _ in fused]
    # a and b tie (each rank 1 + rank 2). Tie broken by chunk id ascending.
    assert {ids[0], ids[1]} == {a.id, b.id}
    assert ids[2] == c.id


def test_rrf_top_k_caps_results() -> None:
    ws = uuid4()
    chunks = [
        Chunk(document_id=uuid4(), workspace_id=ws, ordinal=i, text=str(i))
        for i in range(5)
    ]
    ranking = [(c, 1.0) for c in chunks]
    fused = rrf_combine([ranking], k=60, top_k=2)
    assert len(fused) == 2


def test_rrf_rejects_non_positive_k() -> None:
    with pytest.raises(ValueError):
        rrf_combine([], k=0)


def test_rrf_handles_empty_input() -> None:
    assert rrf_combine([]) == []


def test_rrf_chunk_in_only_one_list_still_ranks() -> None:
    ws = uuid4()
    a = Chunk(document_id=uuid4(), workspace_id=ws, ordinal=0, text="a")
    b = Chunk(document_id=uuid4(), workspace_id=ws, ordinal=1, text="b")
    fused = rrf_combine([[(a, 0.9)], [(b, 0.5)]])
    assert {chunk.id for chunk, _ in fused} == {a.id, b.id}


# ---------------------------------------------------------------------------
# S208: Tombstone registry
# ---------------------------------------------------------------------------


def test_tombstone_marks_and_filters() -> None:
    ws = uuid4()
    doc1, doc2 = uuid4(), uuid4()
    reg = TombstoneRegistry()
    chunks = [
        Chunk(document_id=doc1, workspace_id=ws, ordinal=0, text="keep"),
        Chunk(document_id=doc2, workspace_id=ws, ordinal=0, text="drop"),
    ]
    reg.mark_deleted(workspace_id=ws, document_id=doc2)
    assert reg.is_deleted(workspace_id=ws, document_id=doc2)
    assert not reg.is_deleted(workspace_id=ws, document_id=doc1)
    active = reg.filter_active(workspace_id=ws, chunks=chunks)
    assert [c.document_id for c in active] == [doc1]


def test_tombstone_workspace_isolated() -> None:
    ws_a, ws_b = uuid4(), uuid4()
    doc = uuid4()
    reg = TombstoneRegistry()
    reg.mark_deleted(workspace_id=ws_a, document_id=doc)
    assert reg.is_deleted(workspace_id=ws_a, document_id=doc)
    assert not reg.is_deleted(workspace_id=ws_b, document_id=doc)


def test_tombstone_list_deleted_is_sorted() -> None:
    ws = uuid4()
    docs = [uuid4() for _ in range(3)]
    reg = TombstoneRegistry()
    for d in docs:
        reg.mark_deleted(workspace_id=ws, document_id=d)
    listed = reg.list_deleted(workspace_id=ws)
    assert list(listed) == sorted(docs, key=str)


# ---------------------------------------------------------------------------
# S209: Content-hash diff
# ---------------------------------------------------------------------------


def test_content_hash_excludes_chunk_id() -> None:
    ws = uuid4()
    doc = uuid4()
    a = Chunk(document_id=doc, workspace_id=ws, ordinal=0, text="hello")
    b = Chunk(document_id=doc, workspace_id=ws, ordinal=0, text="hello")
    assert a.id != b.id  # generated ids differ
    assert chunk_content_hash(a) == chunk_content_hash(b)


def test_content_hash_changes_with_metadata() -> None:
    ws = uuid4()
    doc = uuid4()
    a = Chunk(document_id=doc, workspace_id=ws, ordinal=0, text="x")
    b = Chunk(
        document_id=doc, workspace_id=ws, ordinal=0, text="x", metadata={"k": "v"}
    )
    assert chunk_content_hash(a) != chunk_content_hash(b)


def test_diff_chunks_no_change_is_noop() -> None:
    ws = uuid4()
    doc = uuid4()
    prev = [Chunk(document_id=doc, workspace_id=ws, ordinal=i, text=f"c{i}") for i in range(3)]
    curr = [Chunk(document_id=doc, workspace_id=ws, ordinal=i, text=f"c{i}") for i in range(3)]
    d = diff_chunks(previous=prev, current=curr)
    assert isinstance(d, ChunkDiff)
    assert d.is_noop
    assert len(d.unchanged) == 3


def test_diff_chunks_detects_add_remove() -> None:
    ws = uuid4()
    doc = uuid4()
    prev = [
        Chunk(document_id=doc, workspace_id=ws, ordinal=0, text="keep"),
        Chunk(document_id=doc, workspace_id=ws, ordinal=1, text="gone"),
    ]
    curr = [
        Chunk(document_id=doc, workspace_id=ws, ordinal=0, text="keep"),
        Chunk(document_id=doc, workspace_id=ws, ordinal=1, text="new"),
    ]
    d = diff_chunks(previous=prev, current=curr)
    assert [c.text for c in d.added] == ["new"]
    assert [c.text for c in d.removed] == ["gone"]
    assert [c.text for c in d.unchanged] == ["keep"]
