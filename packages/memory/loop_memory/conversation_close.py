"""Conversation-close hook for episodic memory (S491).

When a conversation ends (channel closes, idle timeout fires, or the
user calls ``close``) the runtime calls :func:`ingest_closed_conversation`
which:

1. Picks a salience score from the closed turn count + a caller-supplied
   classifier. (Long, escalated, or marked-important conversations score
   higher and survive TTL pruning longer.)
2. Calls the existing ``auto_summarize`` summariser.
3. Embeds the summary via the configured ``Embedder``.
4. Upserts an ``EpisodicEntry`` into the store.

A conversation may be ingested at most once per ``conversation_id``; the
store is keyed on ``conversation_id`` so a retried close call is
idempotent.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from loop_memory.episodic import (
    EMBEDDING_DIM,
    Embedder,
    EpisodicEntry,
    EpisodicError,
    EpisodicStore,
    auto_summarize,
)


class ConversationOutcome(StrEnum):
    RESOLVED = "resolved"
    ABANDONED = "abandoned"
    ESCALATED = "escalated"


@dataclass(frozen=True, slots=True)
class CloseContext:
    """Everything the salience scorer needs about the closed conversation."""

    workspace_id: UUID
    agent_id: UUID
    conversation_id: UUID
    turn_count: int
    outcome: ConversationOutcome
    user_marked_important: bool = False
    closed_at_ms: int = 0

    def __post_init__(self) -> None:
        if self.turn_count < 0:
            raise ValueError("turn_count must be >=0")
        if self.closed_at_ms < 0:
            raise ValueError("closed_at_ms must be >=0")


SalienceFn = Callable[[CloseContext], float]


def default_salience(ctx: CloseContext) -> float:
    """Heuristic salience in [0, 1].

    * Base 0.2.
    * +0.4 if the user marked the conversation important.
    * +0.2 if escalated.
    * +0.1 per 5 turns, capped.
    Returns the value clipped to [0, 1].
    """
    score = 0.2
    if ctx.user_marked_important:
        score += 0.4
    if ctx.outcome is ConversationOutcome.ESCALATED:
        score += 0.2
    score += min(0.4, 0.1 * (ctx.turn_count // 5))
    return max(0.0, min(1.0, score))


async def ingest_closed_conversation(
    *,
    store: EpisodicStore,
    embedder: Embedder,
    ctx: CloseContext,
    messages: Sequence[str],
    salience_fn: SalienceFn = default_salience,
) -> EpisodicEntry:
    """Build + persist an :class:`EpisodicEntry` for a closed conversation."""
    if not messages:
        raise EpisodicError("cannot ingest a conversation with no messages")
    summary = auto_summarize(messages)
    embedding = embedder.embed(summary)
    if len(embedding) != EMBEDDING_DIM:
        raise EpisodicError(
            f"embedder produced dim {len(embedding)}, expected {EMBEDDING_DIM}"
        )
    salience = salience_fn(ctx)
    if not 0.0 <= salience <= 1.0:
        raise EpisodicError(f"salience {salience} not in [0, 1]")
    entry = EpisodicEntry(
        id=ctx.conversation_id,  # one entry per conversation; retry is idempotent
        workspace_id=ctx.workspace_id,
        agent_id=ctx.agent_id,
        conversation_id=ctx.conversation_id,
        summary=summary,
        embedding=tuple(embedding),
        salience=salience,
        ts_ms=ctx.closed_at_ms,
    )
    await store.upsert(entry)
    return entry


__all__ = [
    "CloseContext",
    "ConversationOutcome",
    "SalienceFn",
    "default_salience",
    "ingest_closed_conversation",
]
