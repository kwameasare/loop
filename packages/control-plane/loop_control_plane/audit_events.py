"""Audit-event recording for every cp-api write endpoint — S630.

Public API:

* :class:`AuditEvent` — frozen dataclass for one row.
* :class:`AuditEventStore` — Protocol the cp-api wires to a Postgres
  ``audit_events`` table; tests use :class:`InMemoryAuditEventStore`.
* :func:`record_audit_event` — validate-and-insert helper.
* :func:`audited` — decorator that wraps an async write method on a
  cp-api service so every successful call emits one event.

Design notes:

The audit trail is append-only at the storage layer (see
``cp_0005_audit_events`` migration: RULE ... DO INSTEAD NOTHING on
UPDATE / DELETE). The Python helper here MUST treat that as a hard
contract — it never exposes ``update`` or ``delete`` methods.

The decorator captures the actor and workspace from the wrapped
method's keyword arguments so call-sites stay one-liners. A write
that raises records ``outcome='error'``; a write that raises
:class:`AuthorisationError` records ``outcome='denied'``. Read
methods are deliberately not decorated — audit volume must stay
proportional to mutation volume.
"""

from __future__ import annotations

import functools
import hashlib
import json
import uuid
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

__all__ = [
    "AuditEvent",
    "AuditEventError",
    "AuditEventStore",
    "InMemoryAuditEventStore",
    "audited",
    "hash_payload",
    "record_audit_event",
]


_VALID_OUTCOMES = frozenset({"success", "denied", "error"})
_MAX_FIELD_LEN = 256


class AuditEventError(ValueError):
    """Raised for invalid event payloads (empty fields, bad outcome, ...)."""


@dataclass(frozen=True, slots=True)
class AuditEvent:
    id: uuid.UUID
    occurred_at: datetime
    workspace_id: uuid.UUID
    actor_sub: str
    action: str
    resource_type: str
    resource_id: str | None
    request_id: str | None
    payload_hash: str | None
    outcome: str  # 'success' | 'denied' | 'error'


class AuditEventStore(Protocol):
    """Persistence seam — production wiring INSERTs into ``audit_events``."""

    def insert(self, event: AuditEvent) -> None: ...

    def list_for_workspace(
        self, workspace_id: uuid.UUID
    ) -> Iterable[AuditEvent]: ...


@dataclass
class InMemoryAuditEventStore:
    """Reference implementation used by tests and offline tooling."""

    _rows: list[AuditEvent] = field(default_factory=list)

    def insert(self, event: AuditEvent) -> None:
        # Append-only — even the in-memory implementation refuses to
        # accept a write that would replace an existing id (defence in
        # depth against a buggy caller).
        for existing in self._rows:
            if existing.id == event.id:
                raise AuditEventError(f"audit event id {event.id} already recorded")
        self._rows.append(event)

    def list_for_workspace(
        self, workspace_id: uuid.UUID
    ) -> tuple[AuditEvent, ...]:
        return tuple(
            sorted(
                (r for r in self._rows if r.workspace_id == workspace_id),
                key=lambda r: r.occurred_at,
            )
        )

    def all(self) -> tuple[AuditEvent, ...]:
        return tuple(self._rows)


def hash_payload(payload: object) -> str:
    """Stable SHA-256 of a JSON-serialisable payload, hex-encoded."""
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_field(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise AuditEventError(f"{name} must be a non-empty string")
    if len(value) > _MAX_FIELD_LEN:
        raise AuditEventError(
            f"{name} exceeds {_MAX_FIELD_LEN} character limit"
        )


def record_audit_event(
    *,
    workspace_id: uuid.UUID,
    actor_sub: str,
    action: str,
    resource_type: str,
    store: AuditEventStore,
    resource_id: str | None = None,
    request_id: str | None = None,
    payload: object | None = None,
    outcome: str = "success",
    now: datetime | None = None,
) -> AuditEvent:
    """Validate inputs and emit a single audit event.

    Returns the persisted :class:`AuditEvent`.
    """
    _validate_field("actor_sub", actor_sub)
    _validate_field("action", action)
    _validate_field("resource_type", resource_type)
    if outcome not in _VALID_OUTCOMES:
        raise AuditEventError(
            f"outcome {outcome!r} not one of {sorted(_VALID_OUTCOMES)}"
        )
    if resource_id is not None and not isinstance(resource_id, str):
        raise AuditEventError("resource_id must be a string when provided")
    if request_id is not None and not isinstance(request_id, str):
        raise AuditEventError("request_id must be a string when provided")
    payload_hash = hash_payload(payload) if payload is not None else None
    event = AuditEvent(
        id=uuid.uuid4(),
        occurred_at=now or datetime.now(UTC),
        workspace_id=workspace_id,
        actor_sub=actor_sub,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        request_id=request_id,
        payload_hash=payload_hash,
        outcome=outcome,
    )
    store.insert(event)
    return event


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


def audited(
    *,
    action: str,
    resource_type: str,
    store_attr: str = "audit_store",
    actor_kwarg: str = "caller_sub",
    workspace_kwarg: str = "workspace_id",
    resource_id_kwarg: str | None = None,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Decorator that emits a single audit event per successful call.

    Pulls the audit store off ``self.<store_attr>``; pulls actor /
    workspace identifiers off the wrapped method's kwargs. Records
    ``outcome='denied'`` for ``AuthorisationError`` (subclass of
    :class:`PermissionError`) and ``outcome='error'`` for any other
    exception, then re-raises so the caller's HTTP error mapping
    still fires.
    """

    def decorator(
        method: Callable[..., Awaitable[Any]],
    ) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(method)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            store: AuditEventStore | None = getattr(self, store_attr, None)
            if store is None:
                # Decorator must be a no-op when the store is not wired,
                # so unit tests can construct services without an audit
                # backend.
                return await method(self, *args, **kwargs)
            actor = kwargs.get(actor_kwarg)
            workspace_id = kwargs.get(workspace_kwarg)
            resource_id = (
                kwargs.get(resource_id_kwarg)
                if resource_id_kwarg is not None
                else None
            )
            try:
                result = await method(self, *args, **kwargs)
            except PermissionError:
                if isinstance(workspace_id, uuid.UUID) and isinstance(actor, str):
                    record_audit_event(
                        workspace_id=workspace_id,
                        actor_sub=actor,
                        action=action,
                        resource_type=resource_type,
                        store=store,
                        resource_id=str(resource_id) if resource_id else None,
                        outcome="denied",
                    )
                raise
            except Exception:
                if isinstance(workspace_id, uuid.UUID) and isinstance(actor, str):
                    record_audit_event(
                        workspace_id=workspace_id,
                        actor_sub=actor,
                        action=action,
                        resource_type=resource_type,
                        store=store,
                        resource_id=str(resource_id) if resource_id else None,
                        outcome="error",
                    )
                raise
            if isinstance(actor, str) and actor.strip():
                # workspace_id may be carried inside the result body for
                # endpoints that create the workspace itself; fall back
                # to that when the kwarg is absent.
                effective_ws = workspace_id
                if not isinstance(effective_ws, uuid.UUID) and isinstance(
                    result, dict
                ):
                    raw = result.get("id") or result.get("workspace_id")
                    if isinstance(raw, str):
                        try:
                            effective_ws = uuid.UUID(raw)
                        except ValueError:
                            effective_ws = None
                    elif isinstance(raw, uuid.UUID):
                        effective_ws = raw
                if isinstance(effective_ws, uuid.UUID):
                    record_audit_event(
                        workspace_id=effective_ws,
                        actor_sub=actor,
                        action=action,
                        resource_type=resource_type,
                        store=store,
                        resource_id=str(resource_id) if resource_id else None,
                        outcome="success",
                    )
            return result

        return wrapper

    return decorator
