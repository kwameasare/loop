"""Pass9 memory tests: conversation_close (S491)."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

import pytest
from loop_memory import langmem_summarize
from loop_memory.conversation_close import (
    CloseContext,
    ConversationOutcome,
    default_salience,
    ingest_closed_conversation,
)
from loop_memory.episodic import (
    EMBEDDING_DIM,
    EpisodicError,
    HashEmbedder,
    InMemoryEpisodicStore,
)


def _ctx(**overrides: object) -> CloseContext:
    base: dict[str, object] = dict(
        workspace_id=uuid4(),
        agent_id=uuid4(),
        conversation_id=uuid4(),
        turn_count=4,
        outcome=ConversationOutcome.RESOLVED,
        user_marked_important=False,
        closed_at_ms=0,
    )
    base.update(overrides)
    return CloseContext(**base)  # type: ignore[arg-type]


def test_default_salience_clipped_into_unit_interval() -> None:
    s = default_salience(_ctx())
    assert 0.0 <= s <= 1.0


def test_default_salience_important_outranks_resolved() -> None:
    a = default_salience(_ctx(user_marked_important=True))
    b = default_salience(_ctx())
    assert a > b


def test_default_salience_escalation_bonus() -> None:
    a = default_salience(_ctx(outcome=ConversationOutcome.ESCALATED, turn_count=0))
    b = default_salience(_ctx(outcome=ConversationOutcome.RESOLVED, turn_count=0))
    assert a > b


def test_default_salience_caps_turn_bonus() -> None:
    s = default_salience(_ctx(turn_count=10_000, user_marked_important=True))
    assert abs(s - 1.0) < 1e-9


def test_close_context_validates_negative_fields() -> None:
    with pytest.raises(ValueError):
        _ctx(turn_count=-1)
    with pytest.raises(ValueError):
        _ctx(closed_at_ms=-1)


@pytest.mark.asyncio
async def test_ingest_closed_conversation_persists_entry() -> None:
    store = InMemoryEpisodicStore()
    embedder = HashEmbedder()
    ctx = _ctx()
    entry = await ingest_closed_conversation(
        store=store,
        embedder=embedder,
        ctx=ctx,
        messages=["hello", "world"],
    )
    assert entry.conversation_id == ctx.conversation_id
    assert entry.id == ctx.conversation_id  # id == conversation_id for idempotency
    assert len(entry.embedding) == EMBEDDING_DIM
    assert 0.0 <= entry.salience <= 1.0
    assert entry.summary  # non-empty
    recent = await store.list_recent(
        workspace_id=ctx.workspace_id, agent_id=ctx.agent_id, limit=10
    )
    assert len(recent) == 1


@pytest.mark.asyncio
async def test_ingest_is_idempotent_per_conversation() -> None:
    store = InMemoryEpisodicStore()
    embedder = HashEmbedder()
    ctx = _ctx()
    await ingest_closed_conversation(
        store=store, embedder=embedder, ctx=ctx, messages=["a"]
    )
    await ingest_closed_conversation(
        store=store, embedder=embedder, ctx=ctx, messages=["a", "b"]
    )
    recent = await store.list_recent(
        workspace_id=ctx.workspace_id, agent_id=ctx.agent_id, limit=10
    )
    assert len(recent) == 1


@pytest.mark.asyncio
async def test_ingest_rejects_empty_messages() -> None:
    store = InMemoryEpisodicStore()
    embedder = HashEmbedder()
    with pytest.raises(EpisodicError):
        await ingest_closed_conversation(
            store=store, embedder=embedder, ctx=_ctx(), messages=[]
        )


@pytest.mark.asyncio
async def test_ingest_rejects_wrong_embedding_dim() -> None:
    class BadEmbedder:
        def embed(self, text: str) -> tuple[float, ...]:
            return (1.0, 0.0)  # wrong dim

    store = InMemoryEpisodicStore()
    with pytest.raises(EpisodicError):
        await ingest_closed_conversation(
            store=store, embedder=BadEmbedder(), ctx=_ctx(), messages=["hi"]
        )


@pytest.mark.asyncio
async def test_ingest_rejects_out_of_range_salience() -> None:
    store = InMemoryEpisodicStore()
    embedder = HashEmbedder()
    with pytest.raises(EpisodicError):
        await ingest_closed_conversation(
            store=store,
            embedder=embedder,
            ctx=_ctx(),
            messages=["hi"],
            salience_fn=lambda _ctx: 1.5,
        )


@pytest.mark.asyncio
async def test_ingest_uses_custom_salience_fn() -> None:
    store = InMemoryEpisodicStore()
    embedder = HashEmbedder()
    entry = await ingest_closed_conversation(
        store=store,
        embedder=embedder,
        ctx=_ctx(),
        messages=["hi"],
        salience_fn=lambda _ctx: 0.42,
    )
    assert abs(entry.salience - 0.42) < 1e-9


@pytest.mark.asyncio
async def test_ingest_accepts_langmem_summarizer_variant() -> None:
    def summarize(messages: Sequence[str], *, max_chars: int = 240) -> str:
        assert max_chars > 0
        return langmem_summarize(messages, max_chars=120)

    store = InMemoryEpisodicStore()
    embedder = HashEmbedder()
    entry = await ingest_closed_conversation(
        store=store,
        embedder=embedder,
        ctx=_ctx(),
        messages=[
            " ".join(["small talk about onboarding"] * 30),
            "User needs Datadog SIEM webhook export for audit evidence.",
        ],
        summarizer=summarize,
    )
    assert "datadog" in entry.summary.lower()
