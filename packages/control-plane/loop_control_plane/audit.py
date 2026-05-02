"""Append-only audit log primitives for control-plane state changes."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

JsonObject = dict[str, Any]


class AuditLogError(ValueError):
    """Raised when an audit event is malformed or the chain is invalid."""


@dataclass(frozen=True)
class AuditContext:
    actor: str
    ip: str
    user_agent: str
    request_id: str
    trace_id: str
    idempotency_key: str | None = None

    @classmethod
    def internal(cls, *, actor: str) -> AuditContext:
        return cls(
            actor=actor,
            ip="127.0.0.1",
            user_agent="loop-control-plane/internal",
            request_id="internal",
            trace_id="internal",
        )


@dataclass(frozen=True)
class AuditEventInput:
    context: AuditContext
    workspace_id: UUID
    action: str
    resource_type: str
    resource_id: UUID | str | None
    before: Mapping[str, Any] | None
    after: Mapping[str, Any] | None


@dataclass(frozen=True)
class AuditLogEntry:
    id: UUID
    workspace_id: UUID
    actor: str
    action: str
    resource_type: str
    resource_id: str | None
    before: JsonObject | None
    after: JsonObject | None
    ip: str
    user_agent: str
    request_id: str
    trace_id: str
    previous_hash: str | None
    entry_hash: str
    created_at: datetime
    idempotency_key: str | None = None


class AuditLog(Protocol):
    def append(self, event: AuditEventInput) -> AuditLogEntry: ...


def _require_non_empty(name: str, value: str) -> None:
    if not value:
        raise AuditLogError(f"{name} is required")


def _entry_hash(
    *,
    entry_id: UUID,
    actor: str,
    action: str,
    created_at: datetime,
    previous_hash: str | None,
) -> str:
    payload = "|".join((str(entry_id), actor, action, created_at.isoformat(), previous_hash or ""))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class InMemoryAuditLog:
    _entries: list[AuditLogEntry] = field(default_factory=list)
    _idempotent: dict[tuple[UUID, str, str, str | None, str], AuditLogEntry] = field(
        default_factory=dict
    )

    def append(self, event: AuditEventInput) -> AuditLogEntry:
        for name, value in (
            ("actor", event.context.actor),
            ("action", event.action),
            ("resource_type", event.resource_type),
            ("ip", event.context.ip),
            ("user_agent", event.context.user_agent),
            ("request_id", event.context.request_id),
            ("trace_id", event.context.trace_id),
        ):
            _require_non_empty(name, value)

        resource_id = str(event.resource_id) if event.resource_id is not None else None
        if event.context.idempotency_key:
            key = (
                event.workspace_id,
                event.action,
                event.resource_type,
                resource_id,
                event.context.idempotency_key,
            )
            existing = self._idempotent.get(key)
            if existing is not None:
                return existing

        previous_hash = self._entries[-1].entry_hash if self._entries else None
        created_at = datetime.now(UTC)
        entry_id = uuid4()
        entry = AuditLogEntry(
            id=entry_id,
            workspace_id=event.workspace_id,
            actor=event.context.actor,
            action=event.action,
            resource_type=event.resource_type,
            resource_id=resource_id,
            before=dict(event.before) if event.before is not None else None,
            after=dict(event.after) if event.after is not None else None,
            ip=event.context.ip,
            user_agent=event.context.user_agent,
            request_id=event.context.request_id,
            trace_id=event.context.trace_id,
            previous_hash=previous_hash,
            entry_hash=_entry_hash(
                entry_id=entry_id,
                actor=event.context.actor,
                action=event.action,
                created_at=created_at,
                previous_hash=previous_hash,
            ),
            created_at=created_at,
            idempotency_key=event.context.idempotency_key,
        )
        self._entries.append(entry)
        if event.context.idempotency_key:
            self._idempotent[key] = entry
        return entry

    def entries(self) -> tuple[AuditLogEntry, ...]:
        return tuple(self._entries)

    def verify_chain(self) -> bool:
        previous_hash: str | None = None
        for entry in self._entries:
            if entry.previous_hash != previous_hash:
                return False
            if entry.entry_hash != _entry_hash(
                entry_id=entry.id,
                actor=entry.actor,
                action=entry.action,
                created_at=entry.created_at,
                previous_hash=previous_hash,
            ):
                return False
            previous_hash = entry.entry_hash
        return True


def audit_log_append(audit_log: AuditLog, event: AuditEventInput) -> AuditLogEntry:
    return audit_log.append(event)


__all__ = [
    "AuditContext",
    "AuditEventInput",
    "AuditLog",
    "AuditLogEntry",
    "AuditLogError",
    "InMemoryAuditLog",
    "audit_log_append",
]
