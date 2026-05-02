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
async def test_workspace_cmk_is_immutable_after_create() -> None:
    api = WorkspaceAPI(workspaces=WorkspaceService())
    created = await api.create(caller_sub="owner", body={"name": "Acme", "slug": "acme"})

    with pytest.raises(WorkspaceError, match="tenant_kms_key_id is immutable"):
        await api.patch(
            caller_sub="owner",
            workspace_id=UUID(created["id"]),
            body={"tenant_kms_key_id": "arn:aws:kms:us-east-1:123:key/other"},
        )
