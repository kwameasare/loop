"""Hermetic tests for the agent-registry factory in :mod:`_app_state`."""

from __future__ import annotations

import pytest
from loop_control_plane._app_agents import AgentRegistry, PostgresAgentRegistry
from loop_control_plane._app_state import _default_agent_registry


def test_factory_returns_in_memory_when_postgres_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOOP_CP_USE_POSTGRES", raising=False)
    monkeypatch.delenv("LOOP_CP_DB_URL", raising=False)
    registry = _default_agent_registry()
    assert isinstance(registry, AgentRegistry)


def test_factory_returns_in_memory_when_only_db_url_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOOP_CP_USE_POSTGRES", raising=False)
    monkeypatch.setenv("LOOP_CP_DB_URL", "postgresql+psycopg://user:pw@host/db")
    registry = _default_agent_registry()
    assert isinstance(registry, AgentRegistry)


def test_factory_fails_closed_when_postgres_requested_without_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOOP_CP_USE_POSTGRES", "1")
    monkeypatch.delenv("LOOP_CP_DB_URL", raising=False)
    with pytest.raises(RuntimeError, match="LOOP_CP_DB_URL"):
        _default_agent_registry()


def test_factory_returns_postgres_when_both_env_vars_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOOP_CP_USE_POSTGRES", "1")
    monkeypatch.setenv(
        "LOOP_CP_DB_URL", "postgresql+psycopg://nobody:nopass@127.0.0.1:1/none"
    )
    registry = _default_agent_registry()
    assert isinstance(registry, PostgresAgentRegistry)
