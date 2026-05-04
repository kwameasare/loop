"""Integration tests for :class:`PostgresAuditEventStore` [P0.2].

Each test runs against a real Postgres (testcontainers) with the cp +
dp migrations applied. The shared ``migrated_postgres_engine`` fixture
yields an :class:`Engine` bound to the unprivileged ``loop_app`` role,
which is what the cp-api uses in production — so RLS policies are
exercised exactly as a leaked-credential scenario would surface them.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from loop_control_plane.audit_events import (
    AuditEvent,
    AuditEventError,
    PostgresAuditEventStore,
    record_audit_event,
)
from sqlalchemy import text
from sqlalchemy.engine import Engine

pytestmark = pytest.mark.integration


def _truncate_audit_events(engine: Engine) -> None:
    """Owner-only path to clear the table between tests.

    The append-only RULEs mean DELETE/UPDATE silently no-op for the
    unprivileged role; TRUNCATE bypasses both rules and ownership
    requirements when run as the table owner. We connect as the
    superuser specifically for this teardown.
    """
    admin_url = engine.url.set(username="test", password="test")
    from sqlalchemy import create_engine

    admin_engine = create_engine(admin_url)
    try:
        with admin_engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE audit_events"))
    finally:
        admin_engine.dispose()


@pytest.fixture
def audit_store(migrated_postgres_engine: Engine) -> PostgresAuditEventStore:
    _truncate_audit_events(migrated_postgres_engine)
    return PostgresAuditEventStore(migrated_postgres_engine)


def test_insert_and_list_round_trip(audit_store: PostgresAuditEventStore) -> None:
    ws = uuid.uuid4()
    event = record_audit_event(
        workspace_id=ws,
        actor_sub="auth0|alice",
        action="workspace.create",
        resource_type="workspace",
        resource_id=str(ws),
        store=audit_store,
        payload={"name": "acme"},
        now=datetime(2027, 6, 15, 12, 0, tzinfo=UTC),
    )

    rows = audit_store.list_for_workspace(ws)
    assert rows == (event,)
    assert rows[0].outcome == "success"
    assert rows[0].payload_hash is not None


def test_insert_rejects_duplicate_id(
    audit_store: PostgresAuditEventStore,
) -> None:
    ws = uuid.uuid4()
    ev = AuditEvent(
        id=uuid.uuid4(),
        occurred_at=datetime(2027, 6, 15, 12, 0, tzinfo=UTC),
        workspace_id=ws,
        actor_sub="auth0|alice",
        action="workspace.create",
        resource_type="workspace",
        resource_id=None,
        request_id=None,
        payload_hash=None,
        outcome="success",
    )
    audit_store.insert(ev)
    with pytest.raises(AuditEventError, match="already recorded"):
        audit_store.insert(ev)


def test_list_orders_by_occurred_at_ascending(
    audit_store: PostgresAuditEventStore,
) -> None:
    ws = uuid.uuid4()
    later = record_audit_event(
        workspace_id=ws,
        actor_sub="auth0|alice",
        action="workspace.update",
        resource_type="workspace",
        store=audit_store,
        now=datetime(2027, 6, 16, 0, 0, tzinfo=UTC),
    )
    earlier = record_audit_event(
        workspace_id=ws,
        actor_sub="auth0|alice",
        action="workspace.create",
        resource_type="workspace",
        store=audit_store,
        now=datetime(2027, 6, 15, 0, 0, tzinfo=UTC),
    )
    rows = audit_store.list_for_workspace(ws)
    assert [r.action for r in rows] == [earlier.action, later.action]


def test_list_for_workspace_excludes_other_workspaces(
    audit_store: PostgresAuditEventStore,
) -> None:
    ws_a = uuid.uuid4()
    ws_b = uuid.uuid4()
    record_audit_event(
        workspace_id=ws_a,
        actor_sub="auth0|alice",
        action="workspace.create",
        resource_type="workspace",
        store=audit_store,
    )
    record_audit_event(
        workspace_id=ws_b,
        actor_sub="auth0|bob",
        action="workspace.create",
        resource_type="workspace",
        store=audit_store,
    )

    rows_a = audit_store.list_for_workspace(ws_a)
    rows_b = audit_store.list_for_workspace(ws_b)
    assert {r.actor_sub for r in rows_a} == {"auth0|alice"}
    assert {r.actor_sub for r in rows_b} == {"auth0|bob"}


def test_append_only_rules_silently_drop_update_and_delete(
    migrated_postgres_engine: Engine, audit_store: PostgresAuditEventStore
) -> None:
    """The cp_0005 migration installs RULE ... DO INSTEAD NOTHING on
    UPDATE / DELETE. Verify that an attempt to mutate a row by an app
    role with full DML privilege is silently dropped — a leaked DB
    credential cannot rewrite the audit trail."""
    ws = uuid.uuid4()
    event = record_audit_event(
        workspace_id=ws,
        actor_sub="auth0|alice",
        action="workspace.create",
        resource_type="workspace",
        store=audit_store,
    )

    with migrated_postgres_engine.begin() as conn:
        conn.execute(
            text("UPDATE audit_events SET actor_sub = 'eve' WHERE id = :id"),
            {"id": event.id},
        )
        conn.execute(
            text("DELETE FROM audit_events WHERE id = :id"),
            {"id": event.id},
        )

    rows = audit_store.list_for_workspace(ws)
    assert len(rows) == 1
    assert rows[0].actor_sub == "auth0|alice"


def test_payload_hash_persisted_round_trip(
    audit_store: PostgresAuditEventStore,
) -> None:
    ws = uuid.uuid4()
    event = record_audit_event(
        workspace_id=ws,
        actor_sub="auth0|alice",
        action="api_key.issue",
        resource_type="api_key",
        store=audit_store,
        payload={"name": "ci-deploy", "scopes": ["agents:write"]},
    )
    rows = audit_store.list_for_workspace(ws)
    assert rows[0].payload_hash == event.payload_hash
    assert rows[0].payload_hash is not None
    assert len(rows[0].payload_hash) == 64  # sha256 hex
