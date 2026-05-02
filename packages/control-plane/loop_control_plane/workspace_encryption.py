"""Workspace-scoped envelope encryption helpers for customer-managed KMS keys."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

from loop_control_plane.kms import KMS, KMSError
from loop_control_plane.workspaces import Workspace


class WorkspaceEncryptionError(ValueError):
    """Raised when a workspace payload cannot be encrypted or opened."""


@dataclass(frozen=True)
class WorkspaceEnvelope:
    algorithm: str
    key_ref: str
    encrypted_data_key: bytes
    nonce: bytes
    ciphertext: bytes
    tag: bytes


class WorkspaceEnvelopeEncryption:
    """Envelope encrypt payloads with ``Workspace.tenant_kms_key_id``."""

    algorithm = "loop.workspace-envelope.v1"

    def __init__(self, kms: KMS) -> None:
        self._kms = kms

    def seal(self, *, workspace: Workspace, plaintext: bytes) -> WorkspaceEnvelope:
        key_ref = self._workspace_key_ref(workspace)
        data_key, encrypted_data_key = self._kms.generate_data_key(key_ref=key_ref)
        nonce = hashlib.sha256(key_ref.encode() + encrypted_data_key).digest()[:12]
        ciphertext = self._xor(plaintext, self._stream_key(data_key, nonce, len(plaintext)))
        tag = self._tag(data_key, key_ref, nonce, ciphertext)
        return WorkspaceEnvelope(
            algorithm=self.algorithm,
            key_ref=key_ref,
            encrypted_data_key=encrypted_data_key,
            nonce=nonce,
            ciphertext=ciphertext,
            tag=tag,
        )

    def open(self, *, workspace: Workspace, envelope: WorkspaceEnvelope) -> bytes:
        key_ref = self._workspace_key_ref(workspace)
        if envelope.algorithm != self.algorithm:
            raise WorkspaceEncryptionError("unsupported envelope algorithm")
        if not hmac.compare_digest(envelope.key_ref, key_ref):
            raise WorkspaceEncryptionError("envelope key_ref does not match workspace")
        try:
            data_key = self._kms.decrypt(key_ref=key_ref, ciphertext=envelope.encrypted_data_key)
        except KMSError as exc:
            raise WorkspaceEncryptionError("unable to unwrap workspace data key") from exc
        expected = self._tag(data_key, key_ref, envelope.nonce, envelope.ciphertext)
        if not hmac.compare_digest(expected, envelope.tag):
            raise WorkspaceEncryptionError("envelope authentication failed")
        return self._xor(
            envelope.ciphertext,
            self._stream_key(data_key, envelope.nonce, len(envelope.ciphertext)),
        )

    @staticmethod
    def _workspace_key_ref(workspace: Workspace) -> str:
        if not workspace.tenant_kms_key_id:
            raise WorkspaceEncryptionError("workspace tenant_kms_key_id is required")
        return workspace.tenant_kms_key_id

    @staticmethod
    def _stream_key(data_key: bytes, nonce: bytes, length: int) -> bytes:
        out = b""
        counter = 0
        while len(out) < length:
            out += hashlib.sha256(data_key + nonce + counter.to_bytes(4, "big")).digest()
            counter += 1
        return out[:length]

    @staticmethod
    def _tag(data_key: bytes, key_ref: str, nonce: bytes, ciphertext: bytes) -> bytes:
        return hmac.new(data_key, key_ref.encode() + nonce + ciphertext, hashlib.sha256).digest()

    @staticmethod
    def _xor(body: bytes, key: bytes) -> bytes:
        return bytes(byte ^ key[index % len(key)] for index, byte in enumerate(body))
