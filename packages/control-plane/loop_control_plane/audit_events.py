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
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

from loop_control_plane.audit_redaction import redact_for_audit

__all__ = [
    "AuditEvent",
    "AuditEventError",
    "AuditEventStore",
    "InMemoryAuditEventStore",
    "PostgresAuditEventStore",
    "audited",
    "fetch_payload",
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

    def insert_payload(self, payload_hash: str, payload: object) -> None: ...

    def fetch_payload(self, payload_hash: str) -> object | None: ...

    def list_for_workspace(
        self, workspace_id: uuid.UUID
    ) -> Iterable[AuditEvent]: ...


@dataclass
class InMemoryAuditEventStore:
    """Reference implementation used by tests and offline tooling."""

    _rows: list[AuditEvent] = field(default_factory=list)
    _payloads: dict[str, object] = field(default_factory=dict)

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

    def insert_payload(self, payload_hash: str, payload: object) -> None:
        self._payloads.setdefault(payload_hash, payload)

    def fetch_payload(self, payload_hash: str) -> object | None:
        return self._payloads.get(payload_hash)

    def all(self) -> tuple[AuditEvent, ...]:
        return tuple(self._rows)


def hash_payload(payload: object) -> str:
    """Stable SHA-256 of a JSON-serialisable payload, hex-encoded."""
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def fetch_payload(store: AuditEventStore, payload_hash: str) -> dict[str, Any] | None:
    """Fetch a persisted audit payload by its SHA-256 hex hash."""
    fetch = getattr(store, "fetch_payload", None)
    if fetch is None:
        return None
    payload = fetch(payload_hash)
    return payload if isinstance(payload, dict) else None


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
    redacted_payload = redact_for_audit(payload) if payload is not None else None
    payload_hash = hash_payload(redacted_payload) if redacted_payload is not None else None
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
    if payload_hash is not None:
        insert_payload = getattr(store, "insert_payload", None)
        if insert_payload is not None:
            insert_payload(payload_hash, redacted_payload)
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


# ---------------------------------------------------------------------------
# Postgres-backed store [P0.2]
# ---------------------------------------------------------------------------


class PostgresAuditEventStore:
    """Postgres-backed audit store — INSERTs into the ``audit_events`` table.

    The append-only contract is enforced at three layers:

    1. The Python class deliberately exposes no ``update`` / ``delete``
       methods (same as :class:`InMemoryAuditEventStore`).
    2. The ``audit_events`` table has rules ``DO INSTEAD NOTHING`` on
       UPDATE / DELETE (see migration ``cp_0005_audit_events``).
    3. Tenant-scoped RLS: ``list_for_workspace`` sets the
       ``app.workspace_id`` GUC inside the same transaction so a
       leaked credential can only read its own audit trail.

    Wraps a synchronous SQLAlchemy :class:`~sqlalchemy.engine.Engine`
    because the existing :class:`AuditEventStore` Protocol is sync —
    every cp-api write endpoint already calls
    :func:`record_audit_event` synchronously from inside an async
    handler. A single audit-row INSERT is fast enough that we accept
    the brief event-loop block; a future PR can introduce an async
    Protocol and an :class:`AsyncEngine`-backed store if profiling
    shows it matters.
    """

    def __init__(self, engine: Engine) -> None:
        # Lazy import keeps the SQLAlchemy import off the hot path for
        # in-memory tests that never construct this class.
        self._engine = engine

    @classmethod
    def from_url(cls, database_url: str, *, echo: bool = False) -> PostgresAuditEventStore:
        """Build a store from a SQLAlchemy URL.

        ``database_url`` should use the psycopg driver, e.g.
        ``postgresql+psycopg://user:pw@host/db``. ``pool_pre_ping`` is
        on so that a long-idle connection that the DB has terminated
        gets refreshed before the next INSERT, instead of surfacing a
        ``DisconnectionError`` to a route handler.
        """
        from sqlalchemy import create_engine

        engine = create_engine(
            database_url,
            echo=echo,
            future=True,
            pool_pre_ping=True,
        )
        return cls(engine)

    def insert(self, event: AuditEvent) -> None:
        from sqlalchemy import text
        from sqlalchemy.exc import IntegrityError

        try:
            with self._engine.begin() as conn:
                # The ``audit_events`` policy is ``USING(...)`` only —
                # without an explicit WITH CHECK, Postgres uses the
                # USING expression for INSERT too. Set the GUC inside
                # the same transaction as the INSERT so the policy
                # admits the new row.
                conn.execute(
                    text("SELECT set_config('app.workspace_id', :ws, true)"),
                    {"ws": str(event.workspace_id)},
                )
                conn.execute(
                    text(
                        """
                        INSERT INTO audit_events (
                            id, occurred_at, workspace_id, actor_sub,
                            action, resource_type, resource_id,
                            request_id, payload_hash, outcome
                        ) VALUES (
                            :id, :occurred_at, :workspace_id, :actor_sub,
                            :action, :resource_type, :resource_id,
                            :request_id, :payload_hash, :outcome
                        )
                        """
                    ),
                    {
                        "id": event.id,
                        "occurred_at": event.occurred_at,
                        "workspace_id": event.workspace_id,
                        "actor_sub": event.actor_sub,
                        "action": event.action,
                        "resource_type": event.resource_type,
                        "resource_id": event.resource_id,
                        "request_id": event.request_id,
                        "payload_hash": event.payload_hash,
                        "outcome": event.outcome,
                    },
                )
        except IntegrityError as exc:
            # The audit_events PK is the event id; a duplicate insert
            # raises IntegrityError. Translate to AuditEventError so
            # callers see the same failure mode as the in-memory store.
            raise AuditEventError(
                f"audit event id {event.id} already recorded"
            ) from exc

    def list_for_workspace(
        self, workspace_id: uuid.UUID
    ) -> tuple[AuditEvent, ...]:
        from sqlalchemy import text

        with self._engine.begin() as conn:
            # Set the RLS GUC so the policy on ``audit_events`` lets
            # this transaction read its own workspace's rows.
            conn.execute(
                text("SELECT set_config('app.workspace_id', :ws, true)"),
                {"ws": str(workspace_id)},
            )
            rows = conn.execute(
                text(
                    """
                    SELECT id, occurred_at, workspace_id, actor_sub,
                           action, resource_type, resource_id,
                           request_id, payload_hash, outcome
                      FROM audit_events
                     WHERE workspace_id = :ws
                     ORDER BY occurred_at ASC, id ASC
                    """
                ),
                {"ws": workspace_id},
            ).all()
        return tuple(
            AuditEvent(
                id=_coerce_uuid(row.id),
                occurred_at=row.occurred_at,
                workspace_id=_coerce_uuid(row.workspace_id),
                actor_sub=row.actor_sub,
                action=row.action,
                resource_type=row.resource_type,
                resource_id=row.resource_id,
                request_id=row.request_id,
                payload_hash=row.payload_hash,
                outcome=row.outcome,
            )
            for row in rows
        )


def _coerce_uuid(value: uuid.UUID | str) -> uuid.UUID:
    """Driver-neutral UUID coercion.

    psycopg returns UUID objects natively, but other drivers (and some
    older versions) return strings. Normalise so the dataclass field
    type is honoured.
    """
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
