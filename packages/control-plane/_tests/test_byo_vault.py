"""Tests for BYO Vault integration — S637."""

from __future__ import annotations

import uuid

import pytest
from loop_control_plane.byo_vault import (
    ByoVaultError,
    InMemoryByoVaultStore,
    StubByoVaultClient,
    VaultConfig,
    fetch_secret,
)

WS_A = uuid.UUID("11111111-1111-4111-8111-111111111111")
WS_B = uuid.UUID("22222222-2222-4222-8222-222222222222")


def test_valid_config_round_trips_through_store() -> None:
    cfg = VaultConfig(
        workspace_id=WS_A,
        address="https://vault.acme.example.com:8200",
        role="loop-app",
        namespace="acme/prod",
        mount_path="kv",
    )
    store = InMemoryByoVaultStore()
    store.upsert(cfg)
    assert store.get(WS_A) == cfg
    assert store.get(WS_B) is None


def test_https_required_for_address() -> None:
    with pytest.raises(ByoVaultError):
        VaultConfig(
            workspace_id=WS_A,
            address="http://vault.acme.example.com",
            role="loop-app",
        )


def test_address_must_have_host() -> None:
    with pytest.raises(ByoVaultError):
        VaultConfig(
            workspace_id=WS_A,
            address="https://",
            role="loop-app",
        )


def test_role_pattern_enforced() -> None:
    with pytest.raises(ByoVaultError):
        VaultConfig(
            workspace_id=WS_A,
            address="https://vault.acme.example.com",
            role="bad role with spaces",
        )


def test_mount_path_cannot_be_blank_or_absolute() -> None:
    with pytest.raises(ByoVaultError):
        VaultConfig(
            workspace_id=WS_A,
            address="https://vault.acme.example.com",
            role="loop-app",
            mount_path="",
        )
    with pytest.raises(ByoVaultError):
        VaultConfig(
            workspace_id=WS_A,
            address="https://vault.acme.example.com",
            role="loop-app",
            mount_path="/secret",
        )


def test_namespace_blank_string_rejected() -> None:
    with pytest.raises(ByoVaultError):
        VaultConfig(
            workspace_id=WS_A,
            address="https://vault.acme.example.com",
            role="loop-app",
            namespace="   ",
        )


def test_fetch_secret_uses_workspace_address_and_role() -> None:
    store = InMemoryByoVaultStore()
    store.upsert(
        VaultConfig(
            workspace_id=WS_A,
            address="https://vault.acme.example.com",
            role="loop-acme",
            namespace="acme/prod",
            mount_path="kv",
        )
    )
    store.upsert(
        VaultConfig(
            workspace_id=WS_B,
            address="https://vault.beta.example.com",
            role="loop-beta",
            mount_path="secret",
        )
    )
    client = StubByoVaultClient(
        {
            ("https://vault.acme.example.com", "kv", "stripe"): {
                "key": "sk_acme_xxx"
            },
            ("https://vault.beta.example.com", "secret", "stripe"): {
                "key": "sk_beta_yyy"
            },
        }
    )
    a = fetch_secret(workspace_id=WS_A, path="stripe", store=store, client=client)
    b = fetch_secret(workspace_id=WS_B, path="stripe", store=store, client=client)
    assert a == {"key": "sk_acme_xxx"}
    assert b == {"key": "sk_beta_yyy"}
    assert client.reads[0] == (
        "https://vault.acme.example.com",
        "loop-acme",
        "acme/prod",
        "kv",
        "stripe",
    )
    assert client.reads[1] == (
        "https://vault.beta.example.com",
        "loop-beta",
        None,
        "secret",
        "stripe",
    )


def test_fetch_secret_raises_when_no_config() -> None:
    store = InMemoryByoVaultStore()
    client = StubByoVaultClient()
    with pytest.raises(ByoVaultError):
        fetch_secret(workspace_id=WS_A, path="stripe", store=store, client=client)


def test_fetch_secret_rejects_empty_or_absolute_path() -> None:
    store = InMemoryByoVaultStore()
    store.upsert(
        VaultConfig(
            workspace_id=WS_A,
            address="https://vault.acme.example.com",
            role="loop-app",
        )
    )
    client = StubByoVaultClient()
    with pytest.raises(ByoVaultError):
        fetch_secret(workspace_id=WS_A, path="", store=store, client=client)
    with pytest.raises(ByoVaultError):
        fetch_secret(workspace_id=WS_A, path="/stripe", store=store, client=client)


def test_fetch_secret_propagates_missing_secret() -> None:
    store = InMemoryByoVaultStore()
    store.upsert(
        VaultConfig(
            workspace_id=WS_A,
            address="https://vault.acme.example.com",
            role="loop-app",
        )
    )
    client = StubByoVaultClient()  # empty
    with pytest.raises(ByoVaultError):
        fetch_secret(
            workspace_id=WS_A, path="stripe", store=store, client=client
        )


def test_delete_returns_true_only_on_first_call() -> None:
    store = InMemoryByoVaultStore()
    store.upsert(
        VaultConfig(
            workspace_id=WS_A,
            address="https://vault.acme.example.com",
            role="loop-app",
        )
    )
    assert store.delete(WS_A) is True
    assert store.delete(WS_A) is False
    assert store.get(WS_A) is None


def test_upsert_replaces_existing_config() -> None:
    store = InMemoryByoVaultStore()
    store.upsert(
        VaultConfig(
            workspace_id=WS_A,
            address="https://vault-old.example.com",
            role="old-role",
        )
    )
    store.upsert(
        VaultConfig(
            workspace_id=WS_A,
            address="https://vault-new.example.com",
            role="new-role",
        )
    )
    cfg = store.get(WS_A)
    assert cfg is not None
    assert cfg.address == "https://vault-new.example.com"
    assert cfg.role == "new-role"
