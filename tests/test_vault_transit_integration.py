"""Live integration test for the Vault transit KMS backend (S918).

Runs against a real `vault:1.18` container in dev mode. Gated on
``LOOP_VAULT_INTEGRATION=1`` so it doesn't fire on every CI run; the
hermetic stub-backed unit tests (``packages/control-plane/_tests/
test_vault_transit.py``) cover the Protocol contract.

To run locally::

    docker run --rm -d --name loop-vault-it \\
        -p 8200:8200 -e VAULT_DEV_ROOT_TOKEN_ID=root \\
        -e VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200 \\
        hashicorp/vault:1.18

    docker exec loop-vault-it sh -c \\
        'VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=root \\
         vault secrets enable transit'

    LOOP_VAULT_INTEGRATION=1 \\
        uv run pytest tests/test_vault_transit_integration.py -q

    docker rm -f loop-vault-it
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("LOOP_VAULT_INTEGRATION") != "1",
    reason="LOOP_VAULT_INTEGRATION=1 not set; live Vault test skipped",
)


def _require_hvac() -> None:
    try:
        import hvac  # type: ignore[import-untyped] # noqa: F401
    except ImportError:
        pytest.skip("hvac not installed; install with `uv pip install hvac`")


@pytest.fixture(scope="module")
def vault_address() -> str:
    return os.environ.get("LOOP_VAULT_ADDR", "http://127.0.0.1:8200")


@pytest.fixture(scope="module")
def vault_token() -> str:
    return os.environ.get("LOOP_VAULT_TOKEN", "root")


@pytest.fixture
def transit_kms(vault_address: str, vault_token: str):  # type: ignore[no-untyped-def]
    _require_hvac()
    from loop_control_plane.vault_transit import (
        VaultTransitConfig,
        build_vault_transit_kms,
    )

    config = VaultTransitConfig(
        address=vault_address,
        token=vault_token,
        mount_path=os.environ.get("LOOP_VAULT_TRANSIT_MOUNT", "transit"),
    )
    kms = build_vault_transit_kms(config)
    return kms


def test_live_round_trip(transit_kms) -> None:  # type: ignore[no-untyped-def]
    """Encrypt then decrypt against a live Vault container."""
    plaintext = b"hello live vault"
    ciphertext = transit_kms.encrypt(key_ref="loop-it-roundtrip", plaintext=plaintext)
    assert ciphertext.startswith(b"vault:v1:")
    recovered = transit_kms.decrypt(key_ref="loop-it-roundtrip", ciphertext=ciphertext)
    assert recovered == plaintext


def test_live_generate_data_key(transit_kms) -> None:  # type: ignore[no-untyped-def]
    plaintext, ciphertext = transit_kms.generate_data_key(key_ref="loop-it-datakey")
    assert len(plaintext) == 32  # AES-256
    recovered = transit_kms.decrypt(key_ref="loop-it-datakey", ciphertext=ciphertext)
    assert recovered == plaintext


def test_live_rotate_increments_version(transit_kms) -> None:  # type: ignore[no-untyped-def]
    transit_kms.encrypt(key_ref="loop-it-rotate", plaintext=b"v1")
    v2 = transit_kms.rotate(key_ref="loop-it-rotate")
    assert v2 >= 2
    v3 = transit_kms.rotate(key_ref="loop-it-rotate")
    assert v3 == v2 + 1


def test_live_old_ciphertext_decrypts_after_rotate(transit_kms) -> None:  # type: ignore[no-untyped-def]
    ct_v1 = transit_kms.encrypt(key_ref="loop-it-rotate-decrypt", plaintext=b"original")
    transit_kms.rotate(key_ref="loop-it-rotate-decrypt")
    # Vault keeps prior versions; the v1 ciphertext must still decrypt.
    recovered = transit_kms.decrypt(key_ref="loop-it-rotate-decrypt", ciphertext=ct_v1)
    assert recovered == b"original"


def test_live_sign_returns_versioned_envelope(transit_kms) -> None:  # type: ignore[no-untyped-def]
    sig = transit_kms.sign(key_ref="loop-it-sign", payload=b"audit-event-xyz")
    assert sig.startswith(b"vault:v")
