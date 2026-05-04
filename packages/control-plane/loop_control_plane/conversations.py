"""Conversation read + takeover service (P0.4).

Closes the conversations + takeover slice. The data plane owns the
conversation rows themselves (per-region Postgres), but cp-api needs
a thin façade for the studio's `/inbox` page so operators can:

* List conversations for a given agent.
* Read a single conversation's metadata (subject + last message + state).
* Take over a conversation (= flip the conversation's
  ``operator_taken_over=True`` flag so the runtime hands off to a
  human reviewer).

Production wiring will swap the in-memory store for a thin proxy via
``WorkspaceAPI.forward_data_plane_call`` (which already exists). For
now we ship a deterministic in-memory store so the studio can be
demo'd without spinning up the dp.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

ConversationState = Literal["open", "closed", "in-takeover"]


class ConversationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: UUID
    workspace_id: UUID
    agent_id: UUID
    subject: str
    state: ConversationState
    operator_taken_over: bool
    created_at: datetime
    last_message_at: datetime
    message_count: int = Field(ge=0)


class ConversationDetail(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    summary: ConversationSummary
    last_user_message: str
    last_assistant_message: str
    metadata: dict[str, Any]


class ConversationError(ValueError):
    """Raised on cross-tenant lookups or unknown conversation ids."""


class ConversationService:
    """In-memory conversation registry. Production wires via
    ``WorkspaceAPI.forward_data_plane_call`` to read from the dp's
    per-region Postgres."""

    def __init__(self) -> None:
        self._summaries: dict[UUID, ConversationSummary] = {}
        self._details: dict[UUID, ConversationDetail] = {}
        self._lock = asyncio.Lock()

    async def list_for_agent(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        state: ConversationState | None = None,
    ) -> list[ConversationSummary]:
        async with self._lock:
            rows = [
                s
                for s in self._summaries.values()
                if s.workspace_id == workspace_id
                and s.agent_id == agent_id
                and (state is None or s.state == state)
            ]
            rows.sort(key=lambda s: s.last_message_at, reverse=True)
            return rows

    async def get(
        self, *, workspace_id: UUID, conversation_id: UUID
    ) -> ConversationDetail:
        async with self._lock:
            detail = self._details.get(conversation_id)
            if detail is None or detail.summary.workspace_id != workspace_id:
                raise ConversationError(f"unknown conversation: {conversation_id}")
            return detail

    async def takeover(
        self,
        *,
        workspace_id: UUID,
        conversation_id: UUID,
        operator_sub: str,
        note: str = "",
    ) -> ConversationSummary:
        """Transition a conversation to the ``in-takeover`` state.

        Idempotent: taking over a conversation already in takeover is
        a no-op; we just refresh ``last_message_at`` so the studio
        sees the timestamp.
        """
        async with self._lock:
            summary = self._summaries.get(conversation_id)
            if summary is None or summary.workspace_id != workspace_id:
                raise ConversationError(f"unknown conversation: {conversation_id}")
            updated = summary.model_copy(
                update={
                    "state": "in-takeover",
                    "operator_taken_over": True,
                    "last_message_at": datetime.now(UTC),
                }
            )
            self._summaries[conversation_id] = updated
            # Persist note in the detail metadata so the studio can
            # render "alice took over: <note>".
            detail = self._details.get(conversation_id)
            if detail is not None:
                new_meta = dict(detail.metadata)
                new_meta["operator_takeover"] = {
                    "operator_sub": operator_sub,
                    "note": note,
                    "at": updated.last_message_at.isoformat(),
                }
                self._details[conversation_id] = detail.model_copy(
                    update={"summary": updated, "metadata": new_meta}
                )
            return updated

    # ---------------------------------------------------------------- #
    # Test seam — the dp will inject rows in production via the
    # forward_data_plane_call proxy. Tests use this directly.
    # ---------------------------------------------------------------- #

    async def _seed(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        subject: str,
        last_user_message: str = "",
        last_assistant_message: str = "",
    ) -> ConversationDetail:
        cid = uuid4()
        now = datetime.now(UTC)
        summary = ConversationSummary(
            id=cid,
            workspace_id=workspace_id,
            agent_id=agent_id,
            subject=subject,
            state="open",
            operator_taken_over=False,
            created_at=now,
            last_message_at=now,
            message_count=2,
        )
        detail = ConversationDetail(
            summary=summary,
            last_user_message=last_user_message,
            last_assistant_message=last_assistant_message,
            metadata={},
        )
        async with self._lock:
            self._summaries[cid] = summary
            self._details[cid] = detail
        return detail


def serialise_summary(s: ConversationSummary) -> dict[str, Any]:
    return {
        "id": str(s.id),
        "workspace_id": str(s.workspace_id),
        "agent_id": str(s.agent_id),
        "subject": s.subject,
        "state": s.state,
        "operator_taken_over": s.operator_taken_over,
        "created_at": s.created_at.isoformat(),
        "last_message_at": s.last_message_at.isoformat(),
        "message_count": s.message_count,
    }


def serialise_detail(d: ConversationDetail) -> dict[str, Any]:
    return {
        "summary": serialise_summary(d.summary),
        "last_user_message": d.last_user_message,
        "last_assistant_message": d.last_assistant_message,
        "metadata": d.metadata,
    }


__all__ = [
    "ConversationDetail",
    "ConversationError",
    "ConversationService",
    "ConversationState",
    "ConversationSummary",
    "serialise_detail",
    "serialise_summary",
]
