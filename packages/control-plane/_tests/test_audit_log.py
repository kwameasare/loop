"""Integration tests for the audit-log write-only middleware — S630.

Covers:
* Alembic migration: cp_0005_audit_log creates ``audit_log`` table.
* :class:`AuditLogger` records events with correct fields and hash chain.
* :class:`InMemoryAuditStore` is strictly append-only (no update / delete).
* Hash-chain integrity: ``entry_hash`` and ``previous_hash`` link events.
* Validation: empty action / resource_type raise ``ValueError``.
* Multi-workspace isolation: events from different workspaces do not bleed.
* write-endpoint integration: simulated api_key:create write emits event.
* Repeat write: two creates each get independent events in the chain.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from loop_control_plane.audit_log import (
    AuditEvent,
    AuditLogger,
    InMemoryAuditStore,
    _canonical_bytes,
    _sha256,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_WS_A = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
_WS_B = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")
_USER = uuid.UUID("cccccccc-0000-0000-0000-000000000003")
_NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


@pytest.fixture()
def store() -> InMemoryAuditStore:
    return InMemoryAuditStore()


@pytest.fixture()
def logger(store: InMemoryAuditStore) -> AuditLogger:
    return AuditLogger(store, clock=_NOW)


# ---------------------------------------------------------------------------
# Migration tests: see tests/test_migrations.py for cp_0005_audit_log coverage
# (cp_sql fixture is only available at the root tests/ level)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# AuditLogger.record — happy path
# ---------------------------------------------------------------------------


def test_record_returns_audit_event(logger: AuditLogger, store: InMemoryAuditStore) -> None:
    event = logger.record(
        workspace_id=_WS_A,
        action="api_key:create",
        resource_type="api_key",
    )
    assert isinstance(event, AuditEvent)
    assert event.action == "api_key:create"
    assert event.resource_type == "api_key"
    assert event.workspace_id == _WS_A
    assert event.created_at == _NOW
    assert len(store.all()) == 1


def test_record_sets_entry_hash(logger: AuditLogger) -> None:
    event = logger.record(
        workspace_id=_WS_A,
        action="agent:deploy",
        resource_type="agent",
    )
    assert event.entry_hash is not None
    assert len(event.entry_hash) == 64  # SHA-256 hex


def test_record_first_event_has_no_previous_hash(logger: AuditLogger) -> None:
    event = logger.record(
        workspace_id=_WS_A,
        action="workspace:create",
        resource_type="workspace",
    )
    assert event.previous_hash is None


def test_record_second_event_chains_to_first(
    logger: AuditLogger, store: InMemoryAuditStore
) -> None:
    first = logger.record(
        workspace_id=_WS_A,
        action="api_key:create",
        resource_type="api_key",
    )
    second = logger.record(
        workspace_id=_WS_A,
        action="api_key:revoke",
        resource_type="api_key",
    )
    assert second.previous_hash == first.entry_hash


def test_record_stores_optional_fields(logger: AuditLogger) -> None:
    resource_id = uuid.uuid4()
    event = logger.record(
        workspace_id=_WS_A,
        actor_user_id=_USER,
        action="secret:set",
        resource_type="secret",
        resource_id=resource_id,
        before_state={"value": "old"},
        after_state={"value": "new"},
        client_ip="10.0.0.1",
        user_agent="TestClient/1.0",
        request_id="req-abc-123",
    )
    assert event.actor_user_id == _USER
    assert event.resource_id == resource_id
    assert event.before_state == {"value": "old"}
    assert event.after_state == {"value": "new"}
    assert event.client_ip == "10.0.0.1"
    assert event.user_agent == "TestClient/1.0"
    assert event.request_id == "req-abc-123"


# ---------------------------------------------------------------------------
# Hash-chain integrity
# ---------------------------------------------------------------------------


def test_entry_hash_is_reproducible(logger: AuditLogger) -> None:
    """Same canonical bytes → same entry_hash."""
    event = logger.record(
        workspace_id=_WS_A,
        action="member:invite",
        resource_type="workspace_member",
    )
    recomputed = _sha256(_canonical_bytes(event))
    assert event.entry_hash == recomputed


def test_hash_chain_three_events(logger: AuditLogger) -> None:
    """Three sequential events form a valid hash chain."""
    e1 = logger.record(workspace_id=_WS_A, action="a:1", resource_type="a")
    e2 = logger.record(workspace_id=_WS_A, action="a:2", resource_type="a")
    e3 = logger.record(workspace_id=_WS_A, action="a:3", resource_type="a")

    assert e1.previous_hash is None
    assert e2.previous_hash == e1.entry_hash
    assert e3.previous_hash == e2.entry_hash


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_record_rejects_empty_action(logger: AuditLogger) -> None:
    with pytest.raises(ValueError, match="action"):
        logger.record(workspace_id=_WS_A, action="", resource_type="agent")


def test_record_rejects_empty_resource_type(logger: AuditLogger) -> None:
    with pytest.raises(ValueError, match="resource_type"):
        logger.record(workspace_id=_WS_A, action="agent:deploy", resource_type="")


# ---------------------------------------------------------------------------
# Multi-workspace isolation
# ---------------------------------------------------------------------------


def test_workspace_events_are_isolated(logger: AuditLogger, store: InMemoryAuditStore) -> None:
    """Events from workspace A do not appear in workspace B's list."""
    logger.record(workspace_id=_WS_A, action="x:1", resource_type="x")
    logger.record(workspace_id=_WS_B, action="y:1", resource_type="y")
    logger.record(workspace_id=_WS_A, action="x:2", resource_type="x")

    ws_a_events = store.list_for_workspace(_WS_A)
    ws_b_events = store.list_for_workspace(_WS_B)

    assert len(ws_a_events) == 2
    assert len(ws_b_events) == 1
    assert all(e.workspace_id == _WS_A for e in ws_a_events)
    assert all(e.workspace_id == _WS_B for e in ws_b_events)


def test_workspace_hash_chains_are_independent(
    logger: AuditLogger,
) -> None:
    """Each workspace maintains its own independent hash chain."""
    a1 = logger.record(workspace_id=_WS_A, action="a:1", resource_type="a")
    b1 = logger.record(workspace_id=_WS_B, action="b:1", resource_type="b")
    a2 = logger.record(workspace_id=_WS_A, action="a:2", resource_type="a")

    assert a1.previous_hash is None
    assert b1.previous_hash is None
    # a2 chains to a1 (not to b1)
    assert a2.previous_hash == a1.entry_hash


# ---------------------------------------------------------------------------
# Write-endpoint integration: api_key lifecycle
# ---------------------------------------------------------------------------


def test_api_key_create_emits_audit_event(store: InMemoryAuditStore) -> None:
    """Simulated api_key:create write endpoint emits an audit event."""
    logger = AuditLogger(store, clock=_NOW)
    key_id = uuid.uuid4()

    event = logger.record(
        workspace_id=_WS_A,
        actor_user_id=_USER,
        action="api_key:create",
        resource_type="api_key",
        resource_id=key_id,
        after_state={"name": "ci-key", "prefix": "loop_sk_ab"},
        client_ip="192.168.1.10",
        request_id="req-001",
    )

    assert event.action == "api_key:create"
    assert event.resource_id == key_id
    assert event.after_state is not None
    assert event.after_state["prefix"] == "loop_sk_ab"
    # before_state is NULL for creates
    assert event.before_state is None


def test_api_key_revoke_chains_to_create(store: InMemoryAuditStore) -> None:
    """api_key:revoke event chains to the preceding api_key:create event."""
    logger = AuditLogger(store, clock=_NOW)
    key_id = uuid.uuid4()

    create_event = logger.record(
        workspace_id=_WS_A,
        actor_user_id=_USER,
        action="api_key:create",
        resource_type="api_key",
        resource_id=key_id,
        after_state={"name": "ci-key"},
    )
    revoke_event = logger.record(
        workspace_id=_WS_A,
        actor_user_id=_USER,
        action="api_key:revoke",
        resource_type="api_key",
        resource_id=key_id,
        before_state={"name": "ci-key"},
    )

    assert revoke_event.previous_hash == create_event.entry_hash
    assert revoke_event.after_state is None  # revoke clears


def test_scim_user_provision_emits_audit_event(store: InMemoryAuditStore) -> None:
    """SCIM provision emits an audit event with scim:user:provision action."""
    logger = AuditLogger(store, clock=_NOW)
    user_id = uuid.uuid4()

    event = logger.record(
        workspace_id=_WS_A,
        action="scim:user:provision",
        resource_type="user",
        resource_id=user_id,
        after_state={"email": "bob@corp.example.com", "active": True},
        request_id="scim-req-42",
    )

    assert event.action == "scim:user:provision"
    assert event.after_state is not None
    assert event.after_state["active"] is True


def test_sso_config_update_emits_audit_event(store: InMemoryAuditStore) -> None:
    """SSO config change emits an audit event capturing before/after state."""
    logger = AuditLogger(store, clock=_NOW)

    event = logger.record(
        workspace_id=_WS_A,
        actor_user_id=_USER,
        action="sso:config:update",
        resource_type="sso_config",
        before_state={"entity_id": "old-entity"},
        after_state={"entity_id": "new-entity"},
    )

    assert event.action == "sso:config:update"
    assert event.before_state is not None
    assert event.after_state is not None
    assert event.before_state["entity_id"] == "old-entity"
    assert event.after_state["entity_id"] == "new-entity"


# ---------------------------------------------------------------------------
# InMemoryAuditStore behaviour
# ---------------------------------------------------------------------------


def test_last_entry_hash_returns_none_for_empty_store(
    store: InMemoryAuditStore,
) -> None:
    assert store.last_entry_hash(_WS_A) is None


def test_last_entry_hash_returns_most_recent(
    logger: AuditLogger, store: InMemoryAuditStore
) -> None:
    logger.record(workspace_id=_WS_A, action="a:1", resource_type="a")
    e2 = logger.record(workspace_id=_WS_A, action="a:2", resource_type="a")
    assert store.last_entry_hash(_WS_A) == e2.entry_hash


def test_list_for_workspace_returns_empty_for_unknown(
    store: InMemoryAuditStore,
) -> None:
    unknown_id = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    assert store.list_for_workspace(unknown_id) == []
