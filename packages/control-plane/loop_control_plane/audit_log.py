"""Append-only audit log middleware for cp-api write endpoints — S630.

Every state-mutating operation in the control plane must emit an
:class:`AuditEvent` so that operators and compliance auditors can
reconstruct "who changed what and when" without relying on application
logs (which may be rotated or redacted).

Design constraints
------------------
* **Write-only**: the store exposes ``append()`` but no ``update()`` or
  ``delete()``.  The ``InMemoryAuditStore`` used in tests enforces this
  contract; the production Postgres store relies on the ``CREATE RULE``
  DDL in migration ``cp_0005_audit_log`` to block database-level
  mutations.
* **Hash-chained entries**: each event records ``previous_hash`` (the
  SHA-256 of the workspace's last entry) and ``entry_hash`` (SHA-256 of
  the canonical fields of *this* entry). The chain lets an auditor
  verify neither a row has been inserted out-of-order nor a row has been
  silently dropped.
* **Framework-agnostic**: :class:`AuditLogger` is a plain Python class.
  FastAPI / Starlette middleware wires it into the request lifecycle; the
  business-logic layer (e.g. ``ApiKeyAPI``) calls
  ``logger.record(...)`` explicitly so that test fixtures can inject an
  :class:`InMemoryAuditStore` and assert on emitted events without
  running an HTTP server.

Action taxonomy (``action`` column)
------------------------------------
Use ``resource:verb`` snake-case identifiers, e.g.:

* ``api_key:create``, ``api_key:revoke``
* ``workspace:create``, ``workspace:update``, ``workspace:delete``
* ``agent:deploy``, ``agent:undeploy``
* ``scim:user:provision``, ``scim:user:deprovision``
* ``sso:config:update``
* ``member:invite``, ``member:remove``
* ``secret:set``, ``secret:delete``
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

__all__ = [
    "AuditEvent",
    "AuditLogger",
    "AuditStore",
    "AuditWriteError",
    "InMemoryAuditStore",
]


class AuditWriteError(RuntimeError):
    """Raised when an append to the audit store fails.

    This is a hard error — if the audit store cannot be written to the
    cp-api must return a 500 rather than silently losing the audit trail.
    """


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Immutable record of a single write operation.

    All fields mirror the ``audit_log`` Postgres table columns from
    migration ``cp_0005_audit_log``.  ``id``, ``entry_hash``, and
    ``created_at`` are computed by :class:`AuditLogger` and must not be
    supplied by callers.
    """

    id: uuid.UUID
    workspace_id: uuid.UUID
    action: str
    resource_type: str
    created_at: datetime
    actor_user_id: uuid.UUID | None = None
    resource_id: uuid.UUID | None = None
    before_state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None
    client_ip: str | None = None
    user_agent: str | None = None
    request_id: str | None = None
    previous_hash: str | None = None
    entry_hash: str | None = None


class AuditStore(Protocol):
    """Persistence seam — append-only write and workspace-scoped read.

    Implementations must ensure that ``append()`` is atomic and
    durable before returning.  The production SQLAlchemy store wraps
    the insert in the caller's transaction; tests use
    :class:`InMemoryAuditStore`.
    """

    def append(self, event: AuditEvent) -> None:
        """Persist *event*.  Raises :class:`AuditWriteError` on failure."""
        ...

    def list_for_workspace(self, workspace_id: uuid.UUID) -> list[AuditEvent]:
        """Return all events for *workspace_id* in insertion order."""
        ...

    def last_entry_hash(self, workspace_id: uuid.UUID) -> str | None:
        """Return the ``entry_hash`` of the most recently appended event
        for *workspace_id*, or ``None`` if the workspace has no events yet.
        """
        ...


class InMemoryAuditStore:
    """Reference :class:`AuditStore` for unit and integration tests.

    Thread-safety is not a goal; each test gets its own instance.
    """

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        self._events.append(event)

    def list_for_workspace(self, workspace_id: uuid.UUID) -> list[AuditEvent]:
        return [e for e in self._events if e.workspace_id == workspace_id]

    def last_entry_hash(self, workspace_id: uuid.UUID) -> str | None:
        ws_events = self.list_for_workspace(workspace_id)
        return ws_events[-1].entry_hash if ws_events else None

    def all(self) -> list[AuditEvent]:
        return list(self._events)


# ---------------------------------------------------------------------------
# Hash helpers
# ---------------------------------------------------------------------------


def _canonical_bytes(event: AuditEvent) -> bytes:
    """Deterministic serialisation used for ``entry_hash`` computation.

    We hash the stable identity fields of the event (id, workspace_id,
    actor, action, resource, previous_hash, created_at ISO string).
    JSON serialisation with sorted keys ensures the output is
    deterministic regardless of insertion order in ``before_state`` /
    ``after_state`` dicts.
    """
    doc = {
        "id": str(event.id),
        "workspace_id": str(event.workspace_id),
        "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
        "action": event.action,
        "resource_type": event.resource_type,
        "resource_id": str(event.resource_id) if event.resource_id else None,
        "previous_hash": event.previous_hash,
        "created_at": event.created_at.isoformat(),
    }
    return json.dumps(doc, sort_keys=True).encode()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# AuditLogger
# ---------------------------------------------------------------------------


class AuditLogger:
    """Write-only middleware: compute hashes and emit audit events.

    Usage::

        store = InMemoryAuditStore()
        logger = AuditLogger(store)

        event = logger.record(
            workspace_id=ws_id,
            action="api_key:create",
            resource_type="api_key",
            resource_id=key_id,
            actor_user_id=caller_id,
            after_state={"name": "my-key", "prefix": "loop_sk_ab"},
        )

    The returned :class:`AuditEvent` has ``entry_hash`` and
    ``previous_hash`` already computed and the event has been
    appended to the store.  Callers should not modify the event after
    this call.
    """

    def __init__(self, store: AuditStore, *, clock: datetime | None = None) -> None:
        self._store = store
        self._clock = clock  # injected only in tests for deterministic timestamps

    def _now(self) -> datetime:
        return self._clock if self._clock is not None else datetime.now(UTC)

    def record(
        self,
        *,
        workspace_id: uuid.UUID,
        action: str,
        resource_type: str,
        actor_user_id: uuid.UUID | None = None,
        resource_id: uuid.UUID | None = None,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        client_ip: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> AuditEvent:
        """Build, hash, and append an audit event.

        Args:
            workspace_id: Target workspace.
            action: ``resource:verb`` identifier (e.g. ``"api_key:create"``).
            resource_type: Type of the mutated resource.
            actor_user_id: User who triggered the write, if known.
            resource_id: UUID of the mutated resource.
            before_state: Snapshot of the resource before the change.
            after_state: Snapshot of the resource after the change.
            client_ip: Source IP address from the HTTP request.
            user_agent: User-Agent header value.
            request_id: Idempotency / correlation key from the request.

        Returns:
            The persisted :class:`AuditEvent` (with ``entry_hash`` set).

        Raises:
            :class:`AuditWriteError` if the store rejects the append.
        """
        if not action:
            raise ValueError("action must be a non-empty string")
        if not resource_type:
            raise ValueError("resource_type must be a non-empty string")

        previous_hash = self._store.last_entry_hash(workspace_id)
        now = self._now()
        event_id = uuid.uuid4()

        # Build without entry_hash first so we can serialise the stable fields.
        partial = AuditEvent(
            id=event_id,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            before_state=before_state,
            after_state=after_state,
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            previous_hash=previous_hash,
            created_at=now,
            entry_hash=None,
        )
        entry_hash = _sha256(_canonical_bytes(partial))

        # Re-build as fully immutable event with entry_hash set.
        # Use object.__setattr__ to bypass the frozen dataclass restriction
        # while keeping the single-construction semantics intact.
        event = AuditEvent(
            id=event_id,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            before_state=before_state,
            after_state=after_state,
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            previous_hash=previous_hash,
            created_at=now,
            entry_hash=entry_hash,
        )
        self._store.append(event)
        return event
