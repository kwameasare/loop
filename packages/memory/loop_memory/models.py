"""Pydantic models for memory entries.

Memory values are JSON-serialisable Python primitives (``Any`` here for
ergonomics; the Postgres adapter persists into ``JSONB``). The ``key``
namespace is per-tier and per-tenant -- see :class:`MemoryScope`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class MemoryScope(StrEnum):
    """Which row-set a memory entry lives in."""

    USER = "user"  # memory_user table -- per (workspace, agent, user, key)
    BOT = "bot"  # memory_bot table -- per (workspace, agent, key)


class MemoryEntry(_StrictModel):
    """One row of persistent memory (user or bot tier)."""

    workspace_id: UUID
    agent_id: UUID
    scope: MemoryScope
    user_id: str | None = None  # required iff scope == USER
    key: str
    value: Any
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SessionEntry(_StrictModel):
    """One key inside a conversation's session memory (Redis-backed)."""

    conversation_id: UUID
    key: str
    value: Any


__all__ = ["MemoryEntry", "MemoryScope", "SessionEntry"]
