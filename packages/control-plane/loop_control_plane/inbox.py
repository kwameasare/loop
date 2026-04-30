"""Operator inbox: queue for human takeover of agent conversations.

State machine
-------------

::

    PENDING --(claim)--> CLAIMED --(resolve)--> RESOLVED
        ^                   |
        |                   +--(release)--> PENDING
        |
        +-- escalate ----------- created here

Invariants:

* A conversation may have **at most one open** (PENDING|CLAIMED) inbox
  item at a time. ``escalate()`` is idempotent on the open item -- the
  second call with the same ``conversation_id`` raises ``InboxError``.
* A claim is exclusive: the operator who calls ``claim()`` first wins,
  any concurrent claim by another operator raises ``InboxError``.
* ``release()`` is only valid in CLAIMED state; it returns the item to
  PENDING and clears the operator id, allowing another operator to pick
  it up.
* ``resolve()`` is only valid in CLAIMED state and is terminal.

The store is in-memory for now (S030 surface). Persistence is wired in
S031+ via a Postgres adapter implementing the same protocol.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

InboxStatus = Literal["pending", "claimed", "resolved"]


class InboxError(RuntimeError):
    """Raised on any inbox state-machine violation."""


class InboxItem(BaseModel):
    """A conversation queued for or in human handling."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    id: UUID
    workspace_id: UUID
    agent_id: UUID
    conversation_id: UUID
    user_id: str = Field(min_length=1)
    status: InboxStatus
    reason: str = Field(min_length=1)
    operator_id: str | None = None
    created_at_ms: int = Field(ge=0)
    claimed_at_ms: int | None = None
    resolved_at_ms: int | None = None
    last_message_excerpt: str = ""

    def with_claim(self, *, operator_id: str, claimed_at_ms: int) -> InboxItem:
        return self.model_copy(
            update={
                "status": "claimed",
                "operator_id": operator_id,
                "claimed_at_ms": claimed_at_ms,
            }
        )

    def with_release(self) -> InboxItem:
        return self.model_copy(
            update={"status": "pending", "operator_id": None, "claimed_at_ms": None}
        )

    def with_resolve(self, *, resolved_at_ms: int) -> InboxItem:
        return self.model_copy(
            update={"status": "resolved", "resolved_at_ms": resolved_at_ms}
        )


@dataclass
class InboxQueue:
    """In-memory implementation of the operator inbox.

    Not thread-safe. The control-plane API serialises requests per
    ``conversation_id`` upstream.
    """

    _items: dict[UUID, InboxItem] = field(default_factory=dict)
    # Index for the single-open-item-per-conversation invariant.
    _open_by_conversation: dict[UUID, UUID] = field(default_factory=dict)

    def escalate(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        conversation_id: UUID,
        user_id: str,
        reason: str,
        now_ms: int,
        last_message_excerpt: str = "",
    ) -> InboxItem:
        if conversation_id in self._open_by_conversation:
            raise InboxError(
                f"conversation {conversation_id} already has an open inbox item"
            )
        item = InboxItem(
            id=uuid4(),
            workspace_id=workspace_id,
            agent_id=agent_id,
            conversation_id=conversation_id,
            user_id=user_id,
            status="pending",
            reason=reason,
            created_at_ms=now_ms,
            last_message_excerpt=last_message_excerpt,
        )
        self._items[item.id] = item
        self._open_by_conversation[conversation_id] = item.id
        return item

    def claim(self, item_id: UUID, *, operator_id: str, now_ms: int) -> InboxItem:
        item = self._items.get(item_id)
        if item is None:
            raise InboxError(f"inbox item {item_id} not found")
        if item.status != "pending":
            raise InboxError(
                f"inbox item {item_id} cannot be claimed from status {item.status!r}"
            )
        claimed = item.with_claim(operator_id=operator_id, claimed_at_ms=now_ms)
        self._items[item_id] = claimed
        return claimed

    def release(self, item_id: UUID) -> InboxItem:
        item = self._items.get(item_id)
        if item is None:
            raise InboxError(f"inbox item {item_id} not found")
        if item.status != "claimed":
            raise InboxError(
                f"inbox item {item_id} cannot be released from status {item.status!r}"
            )
        released = item.with_release()
        self._items[item_id] = released
        return released

    def resolve(self, item_id: UUID, *, now_ms: int) -> InboxItem:
        item = self._items.get(item_id)
        if item is None:
            raise InboxError(f"inbox item {item_id} not found")
        if item.status != "claimed":
            raise InboxError(
                f"inbox item {item_id} cannot be resolved from status {item.status!r}"
            )
        resolved = item.with_resolve(resolved_at_ms=now_ms)
        self._items[item_id] = resolved
        # Resolution closes the conversation slot, allowing future escalations.
        self._open_by_conversation.pop(item.conversation_id, None)
        return resolved

    def get(self, item_id: UUID) -> InboxItem:
        item = self._items.get(item_id)
        if item is None:
            raise InboxError(f"inbox item {item_id} not found")
        return item

    def list_pending(self, workspace_id: UUID) -> list[InboxItem]:
        """All PENDING items for a workspace, oldest first."""

        return sorted(
            (
                item
                for item in self._items.values()
                if item.workspace_id == workspace_id and item.status == "pending"
            ),
            key=lambda i: i.created_at_ms,
        )

    def list_claimed_by(self, operator_id: str) -> list[InboxItem]:
        """All CLAIMED items currently assigned to ``operator_id``."""

        return sorted(
            (
                item
                for item in self._items.values()
                if item.status == "claimed" and item.operator_id == operator_id
            ),
            key=lambda i: (i.claimed_at_ms or 0),
        )


__all__ = [
    "InboxError",
    "InboxItem",
    "InboxQueue",
    "InboxStatus",
]
