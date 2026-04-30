"""Workspace-suspension service (S326).

When a workspace's billing falls into a terminal-failed state (S324
``invoice.payment_failed`` after N attempts), or when an operator
flags it manually, we set ``suspended_at_ms`` and reject new mutations
with a 402 error.

The guard surface is intentionally tiny: ``check_writeable(ws)`` and
``check_readable(ws)``. Reads remain available so the user can fix
billing and reactivate; writes (creating runs, deploys, agents) are
blocked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

SuspensionReason = Literal["payment_failed", "manual", "tos_violation"]


class WorkspaceSuspendedError(RuntimeError):
    """Raised when a write is attempted against a suspended workspace."""

    def __init__(
        self, workspace_id: UUID, reason: SuspensionReason, since_ms: int
    ) -> None:
        super().__init__(
            f"workspace {workspace_id} suspended ({reason}) since {since_ms}"
        )
        self.workspace_id = workspace_id
        self.reason: SuspensionReason = reason
        self.since_ms = since_ms


@dataclass(frozen=True)
class SuspensionRecord:
    workspace_id: UUID
    reason: SuspensionReason
    since_ms: int
    note: str = ""


@dataclass
class SuspensionService:
    """In-memory workspace-suspension registry.

    Production wires the same surface against the ``workspaces.suspended_at``
    column; tests use the in-process dict.
    """

    _records: dict[UUID, SuspensionRecord] = field(default_factory=dict)

    def suspend(
        self,
        workspace_id: UUID,
        *,
        reason: SuspensionReason,
        now_ms: int,
        note: str = "",
    ) -> SuspensionRecord:
        existing = self._records.get(workspace_id)
        if existing is not None:
            # Idempotent — keep the original ``since_ms`` so the user
            # can see the original suspension time.
            return existing
        record = SuspensionRecord(
            workspace_id=workspace_id,
            reason=reason,
            since_ms=now_ms,
            note=note,
        )
        self._records[workspace_id] = record
        return record

    def reinstate(self, workspace_id: UUID) -> bool:
        return self._records.pop(workspace_id, None) is not None

    def is_suspended(self, workspace_id: UUID) -> bool:
        return workspace_id in self._records

    def get(self, workspace_id: UUID) -> SuspensionRecord | None:
        return self._records.get(workspace_id)

    def check_writeable(self, workspace_id: UUID) -> None:
        record = self._records.get(workspace_id)
        if record is None:
            return
        raise WorkspaceSuspendedError(
            workspace_id, record.reason, record.since_ms
        )


__all__ = [
    "SuspensionReason",
    "SuspensionRecord",
    "SuspensionService",
    "WorkspaceSuspendedError",
]
