"""Workspace context middleware (S133).

The dp-runtime resolves the active workspace once per request and stashes
it in a contextvar so deeply nested code (tool calls, KB lookups, billing
hooks) can read the active workspace without threading it explicitly.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from uuid import UUID

__all__ = [
    "WorkspaceContext",
    "WorkspaceContextError",
    "current_workspace",
    "use_workspace",
]


class WorkspaceContextError(LookupError):
    """Raised when ``current_workspace`` is called outside a context."""


@dataclass(frozen=True)
class WorkspaceContext:
    """The minimum pinning info every downstream call needs."""

    workspace_id: UUID
    user_sub: str
    request_id: str


_current: ContextVar[WorkspaceContext | None] = ContextVar(
    "loop_runtime_workspace_context", default=None
)


def current_workspace() -> WorkspaceContext:
    """Return the active context or raise WorkspaceContextError."""

    ctx = _current.get()
    if ctx is None:
        raise WorkspaceContextError("no active workspace context")
    return ctx


@asynccontextmanager
async def use_workspace(ctx: WorkspaceContext) -> AsyncIterator[WorkspaceContext]:
    """Async context manager that pins ``ctx`` for the duration of the block."""

    token = _current.set(ctx)
    try:
        yield ctx
    finally:
        _current.reset(token)
