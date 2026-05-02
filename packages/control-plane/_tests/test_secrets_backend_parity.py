"""S778 SecretsBackend parity suite across cloud and Vault backends."""

from __future__ import annotations

import pytest
from loop_control_plane.secrets import (
    SECRETS_BACKENDS,
    SecretAccess,
    SecretsBackendError,
    build_secrets_backend,
)


@pytest.mark.parametrize("backend", SECRETS_BACKENDS)
def test_secret_backends_share_get_set_rotate_contract(backend: str) -> None:
    secrets = build_secrets_backend(backend)

    assert secrets.backend == backend
    assert secrets.set("workspaces/a/llm-key", "sk-old", ttl_seconds=300) == 1
    assert secrets.get("workspaces/a/llm-key") == "sk-old"
    assert secrets.rotate("workspaces/a/llm-key", "sk-new") == 2
    assert secrets.get("workspaces/a/llm-key") == "sk-new"


def test_secret_backends_share_redacted_access_pattern_contract() -> None:
    expected = (
        SecretAccess("set", "workspaces/a/channel-token", 1),
        SecretAccess("get", "workspaces/a/channel-token", 1),
        SecretAccess("rotate", "workspaces/a/channel-token", 2),
        SecretAccess("get", "workspaces/a/channel-token", 2),
        SecretAccess("delete", "workspaces/a/channel-token", 2),
    )

    for backend in SECRETS_BACKENDS:
        secrets = build_secrets_backend(backend)
        secrets.set("workspaces/a/channel-token", "botpress-import-token")
        secrets.get("workspaces/a/channel-token")
        secrets.rotate("workspaces/a/channel-token", "loop-runtime-token")
        secrets.get("workspaces/a/channel-token")
        secrets.delete("workspaces/a/channel-token")

        pattern = secrets.access_pattern()
        assert pattern == expected
        assert "botpress-import-token" not in repr(pattern)
        assert "loop-runtime-token" not in repr(pattern)


def test_secret_contract_rejects_unsupported_or_invalid_operations() -> None:
    with pytest.raises(SecretsBackendError, match="unsupported"):
        build_secrets_backend("local-file")

    secrets = build_secrets_backend("vault")
    with pytest.raises(SecretsBackendError, match="not found"):
        secrets.get("missing")
    with pytest.raises(SecretsBackendError, match="non-empty"):
        secrets.set("", "value")
    with pytest.raises(SecretsBackendError, match="non-empty"):
        secrets.set("workspaces/a/empty", "")
    with pytest.raises(SecretsBackendError, match="ttl_seconds"):
        secrets.set("workspaces/a/token", "value", ttl_seconds=0)
    with pytest.raises(SecretsBackendError, match="not found"):
        secrets.rotate("missing", "value")
