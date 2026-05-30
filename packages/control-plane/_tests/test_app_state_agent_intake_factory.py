"""Hermetic factory tests for durable agent-intake evidence."""

from __future__ import annotations

import pytest

from loop_control_plane._app_state import _default_agent_intake_registry
from loop_control_plane.agent_intake import (
    AgentIntakeRegistry,
    PostgresAgentIntakeRegistry,
)

_FAKE_URL = "postgresql+psycopg://nobody:nopass@127.0.0.1:1/none"


def test_factory_returns_in_memory_when_postgres_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOOP_CP_USE_POSTGRES", raising=False)
    monkeypatch.delenv("LOOP_CP_DB_URL", raising=False)
    assert isinstance(_default_agent_intake_registry(), AgentIntakeRegistry)


def test_factory_fails_closed_without_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOOP_CP_USE_POSTGRES", "1")
    monkeypatch.delenv("LOOP_CP_DB_URL", raising=False)
    with pytest.raises(RuntimeError, match="LOOP_CP_DB_URL"):
        _default_agent_intake_registry()


def test_factory_returns_postgres_when_both_env_vars_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOOP_CP_USE_POSTGRES", "1")
    monkeypatch.setenv("LOOP_CP_DB_URL", _FAKE_URL)
    assert isinstance(_default_agent_intake_registry(), PostgresAgentIntakeRegistry)
