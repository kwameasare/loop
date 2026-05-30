"""Hermetic tests for the BYOC-secret-service factory in :mod:`_app_state`.

Mirrors :mod:`test_app_state_api_keys_factory`. The Postgres branch is
proven by class dispatch only — no real database is touched in this
hermetic suite.
"""

from __future__ import annotations

import pytest

from loop_control_plane._app_state import _default_byoc_secret_service
from loop_control_plane._byoc_secrets import (
    BYOCSecretService,
    PostgresBYOCSecretService,
)


def test_factory_returns_in_memory_when_postgres_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOOP_CP_USE_POSTGRES", raising=False)
    monkeypatch.delenv("LOOP_CP_DB_URL", raising=False)
    svc = _default_byoc_secret_service()
    assert isinstance(svc, BYOCSecretService)


def test_factory_returns_in_memory_when_only_db_url_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOOP_CP_USE_POSTGRES", raising=False)
    monkeypatch.setenv("LOOP_CP_DB_URL", "postgresql+psycopg://user:pw@host/db")
    svc = _default_byoc_secret_service()
    assert isinstance(svc, BYOCSecretService)


def test_factory_fails_closed_when_postgres_requested_without_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOOP_CP_USE_POSTGRES", "1")
    monkeypatch.delenv("LOOP_CP_DB_URL", raising=False)
    with pytest.raises(RuntimeError, match="LOOP_CP_DB_URL"):
        _default_byoc_secret_service()


def test_factory_returns_postgres_when_both_env_vars_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOOP_CP_USE_POSTGRES", "1")
    monkeypatch.setenv(
        "LOOP_CP_DB_URL",
        "postgresql+psycopg://nobody:nopass@127.0.0.1:1/none",
    )
    svc = _default_byoc_secret_service()
    assert isinstance(svc, PostgresBYOCSecretService)
