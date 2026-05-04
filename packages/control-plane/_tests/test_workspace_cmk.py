"""S636 customer-managed KMS key envelope encryption."""

from __future__ import annotations

from uuid import UUID

import pytest
from loop_control_plane.kms import build_kms_backend
from loop_control_plane.workspace_api import WorkspaceAPI
from loop_control_plane.workspace_encryption import (
    WorkspaceEncryptionError,
    WorkspaceEnvelope,
    WorkspaceEnvelopeEncryption,
)
from loop_control_plane.workspaces import WorkspaceError, WorkspaceService


@pytest.mark.asyncio
async def test_workspace_create_records_customer_managed_kms_key() -> None:
    api = WorkspaceAPI(workspaces=WorkspaceService())
    key_ref = "arn:aws:kms:us-east-1:123456789012:key/customer-managed"

    created = await api.create(
        caller_sub="owner",
        body={"name": "Acme", "slug": "acme", "tenant_kms_key_id": key_ref},
    )

    assert created["tenant_kms_key_id"] == key_ref


@pytest.mark.asyncio
async def test_workspace_cmk_envelope_round_trips_with_aws_kms_backend() -> None:
    service = WorkspaceService()
    workspace = await service.create(
        name="Acme",
        slug="acme",
        owner_sub="owner",
        tenant_kms_key_id="arn:aws:kms:us-east-1:123456789012:key/customer-managed",
    )
    encryptor = WorkspaceEnvelopeEncryption(build_kms_backend("aws_kms"))

    envelope = encryptor.seal(workspace=workspace, plaintext=b"customer payload")

    assert envelope.key_ref == workspace.tenant_kms_key_id
    assert envelope.ciphertext != b"customer payload"
    assert envelope.encrypted_data_key.startswith(b"loopkms:aws_kms:")
    assert encryptor.open(workspace=workspace, envelope=envelope) == b"customer payload"


@pytest.mark.asyncio
async def test_workspace_cmk_rejects_cross_workspace_and_tampered_payloads() -> None:
    service = WorkspaceService()
    left = await service.create(name="Left", slug="left", owner_sub="owner")
    right = await service.create(name="Right", slug="right", owner_sub="owner")
    encryptor = WorkspaceEnvelopeEncryption(build_kms_backend("vault_transit"))
    envelope = encryptor.seal(workspace=left, plaintext=b"secret")

    with pytest.raises(WorkspaceEncryptionError, match="key_ref"):
        encryptor.open(workspace=right, envelope=envelope)

    tampered = WorkspaceEnvelope(
        algorithm=envelope.algorithm,
        key_ref=envelope.key_ref,
        encrypted_data_key=envelope.encrypted_data_key,
        nonce=envelope.nonce,
        ciphertext=envelope.ciphertext + b"x",
        tag=envelope.tag,
    )
    with pytest.raises(WorkspaceEncryptionError, match="authentication"):
        encryptor.open(workspace=left, envelope=tampered)


@pytest.mark.asyncio
async def test_seal_uses_aes_gcm_v2_algorithm() -> None:
    """P0.8a: seal() must always write AES-GCM (`v2`); the legacy
    `v1` XOR-stream construction is open-only for backward compat."""
    service = WorkspaceService()
    workspace = await service.create(name="Acme", slug="acme", owner_sub="owner")
    encryptor = WorkspaceEnvelopeEncryption(build_kms_backend("aws_kms"))
    envelope = encryptor.seal(workspace=workspace, plaintext=b"hello")
    assert envelope.algorithm == "loop.workspace-envelope.v2"
    # GCM tag is always 16 bytes; nonce is 12.
    assert len(envelope.tag) == 16
    assert len(envelope.nonce) == 12


@pytest.mark.asyncio
async def test_v2_envelope_round_trips() -> None:
    """Smoke: encrypt/decrypt different-sized payloads through AES-GCM."""
    service = WorkspaceService()
    workspace = await service.create(name="Acme", slug="acme", owner_sub="owner")
    encryptor = WorkspaceEnvelopeEncryption(build_kms_backend("aws_kms"))

    for payload in (b"", b"x", b"some longer payload " * 100, b"\x00\x01\x02"):
        envelope = encryptor.seal(workspace=workspace, plaintext=payload)
        assert encryptor.open(workspace=workspace, envelope=envelope) == payload


@pytest.mark.asyncio
async def test_v2_aad_binds_ciphertext_to_workspace() -> None:
    """Even with KMS access to both workspaces' root keys, swapping a
    ciphertext between workspaces must fail authentication because the
    AAD is keyed off `key_ref`."""
    service = WorkspaceService()
    left = await service.create(
        name="Left",
        slug="left",
        owner_sub="owner",
        tenant_kms_key_id="arn:aws:kms:us-east-1:123:key/left",
    )
    right = await service.create(
        name="Right",
        slug="right",
        owner_sub="owner",
        tenant_kms_key_id="arn:aws:kms:us-east-1:123:key/right",
    )
    encryptor = WorkspaceEnvelopeEncryption(build_kms_backend("aws_kms"))
    envelope = encryptor.seal(workspace=left, plaintext=b"left-only")

    # Forge an envelope claiming to be for `right` while keeping
    # left's ciphertext+nonce+tag. The key_ref check rejects up-front.
    forged = WorkspaceEnvelope(
        algorithm=envelope.algorithm,
        key_ref=right.tenant_kms_key_id,  # type: ignore[arg-type]
        encrypted_data_key=envelope.encrypted_data_key,
        nonce=envelope.nonce,
        ciphertext=envelope.ciphertext,
        tag=envelope.tag,
    )
    with pytest.raises(WorkspaceEncryptionError):
        encryptor.open(workspace=right, envelope=forged)


@pytest.mark.asyncio
async def test_legacy_v1_envelope_still_decrypts() -> None:
    """P0.8a backward compat: callers holding v1 ciphertexts on disk
    must still be able to decrypt during the migration window. We
    construct a v1 envelope using the legacy helpers (preserved as
    private statics) and assert open() handles it."""
    service = WorkspaceService()
    workspace = await service.create(name="Acme", slug="acme", owner_sub="owner")
    encryptor = WorkspaceEnvelopeEncryption(build_kms_backend("aws_kms"))
    key_ref = workspace.tenant_kms_key_id or ""
    plaintext = b"legacy ciphertext"

    # Build a v1 envelope by hand using the legacy (now private) helpers.
    kms = build_kms_backend("aws_kms")
    data_key, encrypted_data_key = kms.generate_data_key(key_ref=key_ref)
    import hashlib

    nonce = hashlib.sha256(key_ref.encode() + encrypted_data_key).digest()[:12]
    ciphertext = WorkspaceEnvelopeEncryption._legacy_xor(
        plaintext,
        WorkspaceEnvelopeEncryption._legacy_stream_key(data_key, nonce, len(plaintext)),
    )
    tag = WorkspaceEnvelopeEncryption._legacy_tag(data_key, key_ref, nonce, ciphertext)
    legacy_envelope = WorkspaceEnvelope(
        algorithm="loop.workspace-envelope.v1",
        key_ref=key_ref,
        encrypted_data_key=encrypted_data_key,
        nonce=nonce,
        ciphertext=ciphertext,
        tag=tag,
    )

    assert encryptor.open(workspace=workspace, envelope=legacy_envelope) == plaintext


@pytest.mark.asyncio
async def test_v2_envelope_rejects_truncated_ciphertext() -> None:
    """Truncating either the ciphertext or the tag must fail GCM
    verification, not silently return partial data."""
    service = WorkspaceService()
    workspace = await service.create(name="Acme", slug="acme", owner_sub="owner")
    encryptor = WorkspaceEnvelopeEncryption(build_kms_backend("aws_kms"))
    envelope = encryptor.seal(workspace=workspace, plaintext=b"some-data-here")

    # Wrong tag length
    wrong_tag = WorkspaceEnvelope(
        algorithm=envelope.algorithm,
        key_ref=envelope.key_ref,
        encrypted_data_key=envelope.encrypted_data_key,
        nonce=envelope.nonce,
        ciphertext=envelope.ciphertext,
        tag=envelope.tag[:-2],  # 14 bytes instead of 16
    )
    with pytest.raises(WorkspaceEncryptionError):
        encryptor.open(workspace=workspace, envelope=wrong_tag)

    # Wrong nonce length
    wrong_nonce = WorkspaceEnvelope(
        algorithm=envelope.algorithm,
        key_ref=envelope.key_ref,
        encrypted_data_key=envelope.encrypted_data_key,
        nonce=envelope.nonce[:-1],
        ciphertext=envelope.ciphertext,
        tag=envelope.tag,
    )
    with pytest.raises(WorkspaceEncryptionError):
        encryptor.open(workspace=workspace, envelope=wrong_nonce)


@pytest.mark.asyncio
async def test_workspace_cmk_is_immutable_after_create() -> None:
    api = WorkspaceAPI(workspaces=WorkspaceService())
    created = await api.create(caller_sub="owner", body={"name": "Acme", "slug": "acme"})

    with pytest.raises(WorkspaceError, match="tenant_kms_key_id is immutable"):
        await api.patch(
            caller_sub="owner",
            workspace_id=UUID(created["id"]),
            body={"tenant_kms_key_id": "arn:aws:kms:us-east-1:123:key/other"},
        )
