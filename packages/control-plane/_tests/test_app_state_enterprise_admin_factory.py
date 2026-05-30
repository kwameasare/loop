"""Hermetic factory tests for the enterprise-admin Postgres dispatchers.

Mirrors :mod:`test_app_state_api_keys_factory` — confirms env-var
dispatch picks the right class. The Postgres branches construct lazy
engines, so no real database is touched here.
"""

from __future__ import annotations

import pytest

from loop_control_plane._app_state import (
    _default_enterprise_signup_store,
    _default_workspace_invite_store,
)
from loop_control_plane.enterprise_admin import (
    InMemoryEnterpriseSignupStore,
    InMemoryWorkspaceInviteStore,
    PostgresEnterpriseSignupStore,
    PostgresWorkspaceInviteStore,
)

_FAKE_URL = "postgresql+psycopg://nobody:nopass@127.0.0.1:1/none"


def test_signup_factory_returns_in_memory_when_postgres_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOOP_CP_USE_POSTGRES", raising=False)
    monkeypatch.delenv("LOOP_CP_DB_URL", raising=False)
    assert isinstance(
        _default_enterprise_signup_store(), InMemoryEnterpriseSignupStore
    )


def test_signup_factory_returns_in_memory_when_only_db_url_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOOP_CP_USE_POSTGRES", raising=False)
    monkeypatch.setenv("LOOP_CP_DB_URL", _FAKE_URL)
    assert isinstance(
        _default_enterprise_signup_store(), InMemoryEnterpriseSignupStore
    )


def test_signup_factory_fails_closed_without_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOOP_CP_USE_POSTGRES", "1")
    monkeypatch.delenv("LOOP_CP_DB_URL", raising=False)
    with pytest.raises(RuntimeError, match="LOOP_CP_DB_URL"):
        _default_enterprise_signup_store()


def test_signup_factory_returns_postgres_when_both_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOOP_CP_USE_POSTGRES", "1")
    monkeypatch.setenv("LOOP_CP_DB_URL", _FAKE_URL)
    assert isinstance(
        _default_enterprise_signup_store(), PostgresEnterpriseSignupStore
    )


def test_invite_factory_returns_in_memory_when_postgres_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOOP_CP_USE_POSTGRES", raising=False)
    monkeypatch.delenv("LOOP_CP_DB_URL", raising=False)
    assert isinstance(
        _default_workspace_invite_store(), InMemoryWorkspaceInviteStore
    )


def test_invite_factory_fails_closed_without_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOOP_CP_USE_POSTGRES", "1")
    monkeypatch.delenv("LOOP_CP_DB_URL", raising=False)
    with pytest.raises(RuntimeError, match="LOOP_CP_DB_URL"):
        _default_workspace_invite_store()


def test_invite_factory_returns_postgres_when_both_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOOP_CP_USE_POSTGRES", "1")
    monkeypatch.setenv("LOOP_CP_DB_URL", _FAKE_URL)
    assert isinstance(
        _default_workspace_invite_store(), PostgresWorkspaceInviteStore
    )
