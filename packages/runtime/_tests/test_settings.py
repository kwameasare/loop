"""Pass6 runtime settings tests."""

from __future__ import annotations

import pytest
from loop_runtime.settings import Settings, load_settings
from pydantic import ValidationError


def test_settings_defaults() -> None:
    s = Settings()
    assert s.service_name == "loop-dp-runtime"
    assert s.bind_port == 8080
    assert s.environment == "dev"


def test_settings_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOOP_RUNTIME_BIND_PORT", "9090")
    monkeypatch.setenv("LOOP_RUNTIME_ENVIRONMENT", "prod")
    monkeypatch.setenv("LOOP_RUNTIME_LOG_LEVEL", "DEBUG")
    s = Settings()
    assert s.bind_port == 9090
    assert s.environment == "prod"
    assert s.log_level == "DEBUG"


def test_settings_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        load_settings(unknown_field="x")  # type: ignore[arg-type]


def test_settings_secret_str_redacted() -> None:
    s = Settings()
    dumped = repr(s.paseto_key)
    assert "change-me" not in dumped


def test_settings_port_bounds() -> None:
    with pytest.raises(ValidationError):
        load_settings(bind_port=70_000)


def test_settings_invalid_environment() -> None:
    with pytest.raises(ValidationError):
        load_settings(environment="qa")  # type: ignore[arg-type]
