"""Hermetic tests for the audit-event-store factory in :mod:`_app_state`.

The factory's job is to pick :class:`InMemoryAuditEventStore` for
unit tests / air-gapped dev and :class:`PostgresAuditEventStore` for
production wiring. The integration test in
``_tests_integration/test_audit_events_postgres.py`` covers the
Postgres path end-to-end against a real database; these tests cover
the env-var dispatch and the fail-closed behaviour without spinning
the container.
"""

from __future__ import annotations

import pytest
from loop_control_plane._app_state import _default_audit_event_store
from loop_control_plane.audit_events import (
    InMemoryAuditEventStore,
    PostgresAuditEventStore,
)


def test_factory_returns_in_memory_when_postgres_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOOP_CP_USE_POSTGRES", raising=False)
    monkeypatch.delenv("LOOP_CP_DB_URL", raising=False)
    store = _default_audit_event_store()
    assert isinstance(store, InMemoryAuditEventStore)


def test_factory_returns_in_memory_when_only_db_url_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Setting only LOOP_CP_DB_URL must NOT flip to Postgres — the
    operator has to explicitly opt in via LOOP_CP_USE_POSTGRES=1.

    Rationale: every other cp module reads LOOP_CP_DB_URL too (alembic
    config, migrations runner, etc.). We don't want a single env var
    to silently swing the audit trail to a fresh database the operator
    didn't intend, mid-rollout."""
    monkeypatch.delenv("LOOP_CP_USE_POSTGRES", raising=False)
    monkeypatch.setenv("LOOP_CP_DB_URL", "postgresql+psycopg://user:pw@host/db")
    store = _default_audit_event_store()
    assert isinstance(store, InMemoryAuditEventStore)


def test_factory_fails_closed_when_postgres_requested_without_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If LOOP_CP_USE_POSTGRES=1 but LOOP_CP_DB_URL is missing, the
    factory must refuse to start rather than silently fall back to
    in-memory (which would lose every audit event on pod restart)."""
    monkeypatch.setenv("LOOP_CP_USE_POSTGRES", "1")
    monkeypatch.delenv("LOOP_CP_DB_URL", raising=False)
    with pytest.raises(RuntimeError, match="LOOP_CP_DB_URL"):
        _default_audit_event_store()


def test_factory_returns_postgres_when_both_env_vars_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The factory builds an Engine but does not connect — the URL is
    deliberately bogus so the lazy connection would fail if anyone
    tried to use it. We only assert the factory wired the right class."""
    monkeypatch.setenv("LOOP_CP_USE_POSTGRES", "1")
    monkeypatch.setenv(
        "LOOP_CP_DB_URL", "postgresql+psycopg://nobody:nopass@127.0.0.1:1/none"
    )
    store = _default_audit_event_store()
    assert isinstance(store, PostgresAuditEventStore)
