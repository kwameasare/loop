"""Tests for the Vault transit KMS backend (S918).

Hermetic — no live Vault. Uses :class:`_VaultTransitClientStub` which
mimics the subset of the ``hvac.Client.secrets.transit.*`` surface that
:class:`loop_control_plane.vault_transit.VaultTransitKMS` calls.

A live integration test exists separately at
``tests/test_vault_transit_integration.py`` and is gated on
``LOOP_VAULT_INTEGRATION=1``.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass, field
from typing import Any

import pytest
from loop_control_plane.kms import KMSError, build_kms_backend
from loop_control_plane.vault_transit import (
    VaultTransitClient,
    VaultTransitConfig,
    VaultTransitKMS,
    build_vault_transit_kms,
)

# --------------------------------------------------------------------------- #
# Stub Vault transit client                                                   #
# --------------------------------------------------------------------------- #


@dataclass
class _StubTransitOps:
    """In-memory mimic of Vault transit. Each key is a list of versions
    (versions are 1-indexed, matching Vault's behaviour). Encryption is a
    deterministic XOR against the version's keystream so we can verify
    decrypt round-trips without depending on real crypto."""

    keys: dict[str, list[bytes]] = field(default_factory=dict[str, list[bytes]])
    encrypt_called: int = 0
    decrypt_called: int = 0
    rotate_called: int = 0
    hmac_called: int = 0
    raise_on_next: BaseException | None = None

    def _get_versions(self, name: str) -> list[bytes]:
        if name not in self.keys:
            # Vault's transit auto-creates keys on first use when policy
            # allows it; for tests we mirror that ergonomic.
            self.keys[name] = [hashlib.sha256(f"v1:{name}".encode()).digest()]
        return self.keys[name]

    @staticmethod
    def _xor(data: bytes, keystream: bytes) -> bytes:
        return bytes(b ^ keystream[i % len(keystream)] for i, b in enumerate(data))

    def _maybe_raise(self) -> None:
        if self.raise_on_next is not None:
            exc = self.raise_on_next
            self.raise_on_next = None
            raise exc

    def encrypt_data(
        self,
        name: str,
        plaintext: str,
        mount_point: str,
    ) -> dict[str, Any]:
        self._maybe_raise()
        self.encrypt_called += 1
        del mount_point  # mirrored in the response envelope
        versions = self._get_versions(name)
        version = len(versions)
        body = base64.b64decode(plaintext)
        ct = self._xor(body, versions[-1])
        ct_b64 = base64.b64encode(ct).decode()
        return {"data": {"ciphertext": f"vault:v{version}:{ct_b64}"}}

    def decrypt_data(
        self,
        name: str,
        ciphertext: str,
        mount_point: str,
    ) -> dict[str, Any]:
        self._maybe_raise()
        self.decrypt_called += 1
        del mount_point
        versions = self._get_versions(name)
        prefix, ver_part, ct_b64 = ciphertext.split(":", 2)
        if prefix != "vault":
            raise ValueError(f"bad ciphertext envelope: {prefix!r}")
        version = int(ver_part.removeprefix("v"))
        keystream = versions[version - 1]
        body = self._xor(base64.b64decode(ct_b64), keystream)
        return {"data": {"plaintext": base64.b64encode(body).decode()}}

    def generate_data_key(
        self,
        name: str,
        key_type: str,
        mount_point: str,
    ) -> dict[str, Any]:
        self._maybe_raise()
        if key_type != "plaintext":
            raise ValueError(f"stub only supports plaintext datakey; got {key_type}")
        del mount_point
        versions = self._get_versions(name)
        version = len(versions)
        # Use a deterministic data key for test stability
        data_key = hashlib.sha256(f"datakey:{name}:v{version}".encode()).digest()
        ct = self._xor(data_key, versions[-1])
        return {
            "data": {
                "plaintext": base64.b64encode(data_key).decode(),
                "ciphertext": f"vault:v{version}:{base64.b64encode(ct).decode()}",
            }
        }

    def rotate_key(self, name: str, mount_point: str) -> dict[str, Any]:
        self._maybe_raise()
        self.rotate_called += 1
        del mount_point
        versions = self._get_versions(name)
        next_v = len(versions) + 1
        versions.append(hashlib.sha256(f"v{next_v}:{name}".encode()).digest())
        return {"data": {}}

    def generate_hmac(
        self,
        name: str,
        hash_input: str,
        mount_point: str,
    ) -> dict[str, Any]:
        self._maybe_raise()
        self.hmac_called += 1
        del mount_point
        versions = self._get_versions(name)
        version = len(versions)
        payload = base64.b64decode(hash_input)
        digest = hashlib.sha256(versions[-1] + payload).digest()
        return {"data": {"hmac": f"vault:v{version}:{base64.b64encode(digest).decode()}"}}

    def read_key(self, name: str, mount_point: str) -> dict[str, Any]:
        del mount_point
        versions = self._get_versions(name)
        return {"data": {"latest_version": len(versions)}}


@dataclass
class _StubSecrets:
    transit: _StubTransitOps


@dataclass
class _VaultTransitClientStub(VaultTransitClient):
    secrets: _StubSecrets


def _stub_client() -> tuple[_VaultTransitClientStub, _StubTransitOps]:
    transit = _StubTransitOps()
    return _VaultTransitClientStub(secrets=_StubSecrets(transit=transit)), transit


# --------------------------------------------------------------------------- #
# Config validation                                                           #
# --------------------------------------------------------------------------- #


def test_config_rejects_relative_url() -> None:
    with pytest.raises(ValueError, match="must start with http"):
        VaultTransitConfig(address="vault.example.com:8200", token="t")


def test_config_rejects_empty_token() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        VaultTransitConfig(address="https://vault.example.com:8200", token="")


def test_config_rejects_absolute_mount() -> None:
    with pytest.raises(ValueError, match="relative path"):
        VaultTransitConfig(
            address="https://vault.example.com:8200",
            token="t",
            mount_path="/transit",
        )


def test_config_rejects_zero_timeout() -> None:
    with pytest.raises(ValueError, match="must be > 0"):
        VaultTransitConfig(
            address="https://vault.example.com:8200",
            token="t",
            timeout_seconds=0,
        )


# --------------------------------------------------------------------------- #
# Round-trip happy paths                                                      #
# --------------------------------------------------------------------------- #


@pytest.fixture
def kms() -> tuple[VaultTransitKMS, _StubTransitOps]:
    config = VaultTransitConfig(
        address="https://vault.example.com:8200",
        token="root",
        mount_path="transit",
    )
    client, transit = _stub_client()
    return VaultTransitKMS(client=client, config=config), transit


def test_encrypt_then_decrypt_roundtrips(
    kms: tuple[VaultTransitKMS, _StubTransitOps],
) -> None:
    backend, transit = kms
    plaintext = b"hello vault transit"
    ciphertext = backend.encrypt(key_ref="workspace-1", plaintext=plaintext)
    assert ciphertext.startswith(b"vault:v1:")
    recovered = backend.decrypt(key_ref="workspace-1", ciphertext=ciphertext)
    assert recovered == plaintext
    assert transit.encrypt_called == 1
    assert transit.decrypt_called == 1


def test_generate_data_key_returns_plaintext_and_ciphertext(
    kms: tuple[VaultTransitKMS, _StubTransitOps],
) -> None:
    backend, _ = kms
    plaintext, ciphertext = backend.generate_data_key(key_ref="ws-2")
    assert len(plaintext) == 32  # sha256
    # Decrypting the wrapped ciphertext yields the same plaintext.
    recovered = backend.decrypt(key_ref="ws-2", ciphertext=ciphertext)
    assert recovered == plaintext


def test_rotate_returns_new_version(
    kms: tuple[VaultTransitKMS, _StubTransitOps],
) -> None:
    backend, transit = kms
    backend.encrypt(key_ref="ws-3", plaintext=b"x")
    assert backend.rotate(key_ref="ws-3") == 2
    assert backend.rotate(key_ref="ws-3") == 3
    assert transit.rotate_called == 2


def test_rotate_old_ciphertext_still_decrypts(
    kms: tuple[VaultTransitKMS, _StubTransitOps],
) -> None:
    backend, _ = kms
    ct_v1 = backend.encrypt(key_ref="ws-rotate", plaintext=b"original")
    backend.rotate(key_ref="ws-rotate")
    ct_v2 = backend.encrypt(key_ref="ws-rotate", plaintext=b"after-rotate")
    # Both decrypt cleanly through Vault even after rotation, because
    # Vault tracks every key version.
    assert backend.decrypt(key_ref="ws-rotate", ciphertext=ct_v1) == b"original"
    assert backend.decrypt(key_ref="ws-rotate", ciphertext=ct_v2) == b"after-rotate"
    assert ct_v1.startswith(b"vault:v1:")
    assert ct_v2.startswith(b"vault:v2:")


def test_sign_returns_versioned_envelope(
    kms: tuple[VaultTransitKMS, _StubTransitOps],
) -> None:
    backend, _ = kms
    sig = backend.sign(key_ref="ws-sign", payload=b"audit-event-123")
    assert sig.startswith(b"vault:v1:")


# --------------------------------------------------------------------------- #
# Error paths                                                                 #
# --------------------------------------------------------------------------- #


def test_empty_key_ref_rejected(
    kms: tuple[VaultTransitKMS, _StubTransitOps],
) -> None:
    backend, _ = kms
    with pytest.raises(KMSError, match="non-empty"):
        backend.encrypt(key_ref="", plaintext=b"x")


def test_path_separators_rejected(
    kms: tuple[VaultTransitKMS, _StubTransitOps],
) -> None:
    backend, _ = kms
    with pytest.raises(KMSError, match="path separators"):
        backend.encrypt(key_ref="../etc/passwd", plaintext=b"x")


def test_upstream_failure_wraps_in_kms_error(
    kms: tuple[VaultTransitKMS, _StubTransitOps],
) -> None:
    backend, transit = kms
    transit.raise_on_next = RuntimeError("503 Vault sealed")
    with pytest.raises(KMSError, match="encrypt failed.*503 Vault sealed"):
        backend.encrypt(key_ref="ws", plaintext=b"x")


def test_malformed_ciphertext_decode_fails_gracefully(
    kms: tuple[VaultTransitKMS, _StubTransitOps],
) -> None:
    backend, _ = kms
    with pytest.raises(KMSError, match="not utf-8"):
        backend.decrypt(key_ref="ws", ciphertext=b"\xff\xfe\xfd")


def test_response_missing_data_field_raises(
    kms: tuple[VaultTransitKMS, _StubTransitOps],
) -> None:
    backend, transit = kms

    def broken_encrypt(name: str, plaintext: str, mount_point: str) -> dict[str, Any]:
        del name, plaintext, mount_point
        return {"data": {"unrelated": "field"}}

    transit.encrypt_data = broken_encrypt  # type: ignore[method-assign]
    with pytest.raises(KMSError, match="missing string field 'ciphertext'"):
        backend.encrypt(key_ref="ws", plaintext=b"x")


# --------------------------------------------------------------------------- #
# Factory dispatch                                                            #
# --------------------------------------------------------------------------- #


def test_build_kms_backend_returns_vault_transit_with_config() -> None:
    config = VaultTransitConfig(
        address="https://vault.example.com:8200",
        token="root",
    )
    client, _ = _stub_client()
    kms = build_kms_backend("vault_transit", config=config, client=client)
    assert isinstance(kms, VaultTransitKMS)
    assert kms.backend == "vault_transit"
    assert kms.config is config


def test_build_kms_backend_falls_back_to_inmemory_without_config() -> None:
    # Without a config kwarg the factory keeps the legacy InMemoryKMS path
    # so unit tests that just want a deterministic backend keep working.
    kms = build_kms_backend("vault_transit")
    assert kms.backend == "vault_transit"
    # InMemoryKMS — the factory didn't dispatch to VaultTransitKMS.
    assert not isinstance(kms, VaultTransitKMS)


def test_build_kms_backend_rejects_wrong_config_type() -> None:
    with pytest.raises(KMSError, match="VaultTransitConfig"):
        build_kms_backend("vault_transit", config="not-a-config")  # type: ignore[arg-type]


def test_build_vault_transit_kms_with_custom_client() -> None:
    config = VaultTransitConfig(
        address="https://vault.example.com:8200",
        token="root",
    )
    client, _ = _stub_client()
    kms = build_vault_transit_kms(config, client=client)
    assert isinstance(kms, VaultTransitKMS)
    assert kms.client is client
