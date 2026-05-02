"""Per-user memory isolation helpers for the runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

__all__ = ["MemoryAuditEvent", "MemoryScope", "UserMemoryStore"]


@dataclass(frozen=True)
class MemoryScope:
    workspace_id: UUID
    agent_id: UUID
    user_id: str

    def __post_init__(self) -> None:
        if not self.user_id:
            raise ValueError("user_id must be non-empty")


@dataclass(frozen=True)
class MemoryAuditEvent:
    action: str
    workspace_id: UUID
    agent_id: UUID
    user_id: str
    key: str
    allowed: bool


@dataclass
class UserMemoryStore:
    _records: dict[tuple[UUID, UUID, str, str], Any] = field(
        default_factory=dict[tuple[UUID, UUID, str, str], Any]
    )
    _audit: list[MemoryAuditEvent] = field(default_factory=list[MemoryAuditEvent])

    def put(self, scope: MemoryScope, key: str, value: Any) -> None:
        self._validate_key(key)
        self._records[self._entry(scope, key)] = value
        self._record("put", scope, key, allowed=True)

    def get(self, scope: MemoryScope, key: str) -> Any | None:
        self._validate_key(key)
        entry = self._entry(scope, key)
        allowed = entry in self._records
        self._record("get", scope, key, allowed=allowed)
        return self._records.get(entry)

    def list_for_user(self, scope: MemoryScope) -> dict[str, Any]:
        out = {
            key: value
            for (workspace_id, agent_id, user_id, key), value in self._records.items()
            if (
                workspace_id == scope.workspace_id
                and agent_id == scope.agent_id
                and user_id == scope.user_id
            )
        }
        self._record("list", scope, "*", allowed=True)
        return out

    def audit_log(self) -> tuple[MemoryAuditEvent, ...]:
        return tuple(self._audit)

    @staticmethod
    def _entry(scope: MemoryScope, key: str) -> tuple[UUID, UUID, str, str]:
        return (scope.workspace_id, scope.agent_id, scope.user_id, key)

    def _record(self, action: str, scope: MemoryScope, key: str, *, allowed: bool) -> None:
        self._audit.append(
            MemoryAuditEvent(
                action=action,
                workspace_id=scope.workspace_id,
                agent_id=scope.agent_id,
                user_id=scope.user_id,
                key=key,
                allowed=allowed,
            )
        )

    @staticmethod
    def _validate_key(key: str) -> None:
        if not key:
            raise ValueError("memory key must be non-empty")
