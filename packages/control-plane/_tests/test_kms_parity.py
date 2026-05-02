"""S777 KMS parity suite across cloud and Vault backends."""

from __future__ import annotations

import pytest
from loop_control_plane.kms import KMS_BACKENDS, KMSError, build_kms_backend


@pytest.mark.parametrize("backend", KMS_BACKENDS)
def test_kms_backends_share_encrypt_decrypt_and_data_key_contract(backend: str) -> None:
    kms = build_kms_backend(backend)
    plaintext = b"customer secret"

    ciphertext = kms.encrypt(key_ref="workspace/a", plaintext=plaintext)
    data_key, encrypted_data_key = kms.generate_data_key(key_ref="workspace/a")

    assert kms.backend == backend
    assert ciphertext.startswith(f"loopkms:{backend}:1:".encode())
    assert kms.decrypt(key_ref="workspace/a", ciphertext=ciphertext) == plaintext
    assert len(data_key) == 32
    assert kms.decrypt(key_ref="workspace/a", ciphertext=encrypted_data_key) == data_key


@pytest.mark.parametrize("backend", KMS_BACKENDS)
def test_kms_backends_share_rotate_and_sign_contract(backend: str) -> None:
    kms = build_kms_backend(backend)
    old_ciphertext = kms.encrypt(key_ref="workspace/a", plaintext=b"before")
    old_signature = kms.sign(key_ref="workspace/a", payload=b"deploy sketch")

    assert kms.rotate(key_ref="workspace/a") == 2
    new_ciphertext = kms.encrypt(key_ref="workspace/a", plaintext=b"after")
    new_signature = kms.sign(key_ref="workspace/a", payload=b"deploy sketch")

    assert kms.decrypt(key_ref="workspace/a", ciphertext=old_ciphertext) == b"before"
    assert kms.decrypt(key_ref="workspace/a", ciphertext=new_ciphertext) == b"after"
    assert old_signature != new_signature
    assert len(new_signature) == 32


def test_kms_contract_rejects_unsupported_or_invalid_operations() -> None:
    with pytest.raises(KMSError, match="unsupported"):
        build_kms_backend("local-file")
    kms = build_kms_backend("aws_kms")
    other = build_kms_backend("gcp_kms")
    ciphertext = kms.encrypt(key_ref="workspace/a", plaintext=b"secret")
    with pytest.raises(KMSError, match="backend mismatch"):
        other.decrypt(key_ref="workspace/a", ciphertext=ciphertext)
    with pytest.raises(KMSError, match="malformed"):
        kms.decrypt(key_ref="workspace/a", ciphertext=b"not-an-envelope")
    with pytest.raises(KMSError, match="key_ref"):
        kms.sign(key_ref="", payload=b"payload")
