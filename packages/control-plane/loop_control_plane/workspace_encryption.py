"""Workspace-scoped envelope encryption helpers for customer-managed KMS keys.

Closes P0.8a from the prod-readiness audit. The previous implementation
used a hand-rolled XOR-stream cipher (``hashlib.sha256(data_key+nonce+
counter)`` keystream) plus an HMAC-SHA256 tag. While not catastrophically
broken, that construction has no NIST validation, no constant-time
decryption guarantees beyond the tag compare, and reviewers would
reject it in any third-party audit.

This module now uses ``cryptography.hazmat.primitives.aead.AESGCM`` for
the data-key path:

  * 256-bit data key from KMS (the unwrapped envelope key); we stretch
    via SHA-256 if the KMS-Protocol implementation returns an unusual
    length.
  * 96-bit random nonce per encryption (NIST recommendation; we use
    full random bits since the KMS issues a fresh data key per call).
  * 128-bit GCM tag bound to the workspace ``key_ref`` via the AAD,
    so swapping a ciphertext between workspaces fails authentication
    even if both workspaces have access to the same KMS root key.

Backward compatibility
======================
The legacy ``loop.workspace-envelope.v1`` algorithm constant is retained
for *open* but rejected for *seal*. Callers holding old envelopes can
still decrypt; new ciphertexts are written as ``v2`` (AES-GCM). When
all on-disk envelopes have been re-encrypted, drop the v1 path.

The legacy path is kept inside the same class so callers don't have to
do `isinstance` checks; they call ``open`` and the method dispatches by
``algorithm`` field.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from loop_control_plane.kms import KMS, KMSError
from loop_control_plane.workspaces import Workspace


class WorkspaceEncryptionError(ValueError):
    """Raised when a workspace payload cannot be encrypted or opened."""


# AES-GCM nonce size (NIST SP 800-38D recommendation).
_NONCE_LEN = 12
# GCM tag is appended to the ciphertext by AESGCM.encrypt; we split it
# back out so the on-disk envelope shape stays explicit (operators can
# eyeball ciphertext vs tag).
_TAG_LEN = 16


@dataclass(frozen=True)
class WorkspaceEnvelope:
    """On-disk envelope shape.

    For ``v2`` (AES-GCM): ``ciphertext`` is the GCM body without the
    appended tag, and ``tag`` is the 16-byte GCM tag.
    For legacy ``v1``: ``ciphertext`` is the XOR-stream output and
    ``tag`` is the HMAC-SHA256 keyed tag (used only on open, not seal).
    """

    algorithm: str
    key_ref: str
    encrypted_data_key: bytes
    nonce: bytes
    ciphertext: bytes
    tag: bytes


class WorkspaceEnvelopeEncryption:
    """Envelope-encrypt payloads with the workspace's KMS root key.

    seal() always writes ``v2`` (AES-GCM). open() supports both ``v2``
    and the legacy ``v1`` so existing on-disk ciphertexts decrypt
    cleanly through the migration window.
    """

    algorithm = "loop.workspace-envelope.v2"
    legacy_algorithm = "loop.workspace-envelope.v1"

    def __init__(self, kms: KMS) -> None:
        self._kms = kms

    # ---------------------------------------------------------------- #
    # Sealing                                                          #
    # ---------------------------------------------------------------- #

    def seal(self, *, workspace: Workspace, plaintext: bytes) -> WorkspaceEnvelope:
        key_ref = self._workspace_key_ref(workspace)
        data_key, encrypted_data_key = self._kms.generate_data_key(key_ref=key_ref)
        if len(data_key) not in (16, 24, 32):
            # KMS Protocol allows any length; AES-GCM requires 128/192/
            # 256-bit keys. Stretch to 32 bytes via SHA-256 if the KMS
            # returned an unusual length so we always end up at AES-256.
            data_key = hashlib.sha256(data_key).digest()
        nonce = os.urandom(_NONCE_LEN)
        aad = self._aad(key_ref)
        try:
            sealed = AESGCM(data_key).encrypt(nonce, plaintext, aad)
        except (TypeError, ValueError) as exc:
            raise WorkspaceEncryptionError("AES-GCM encrypt failed") from exc
        # AESGCM.encrypt returns ciphertext || tag (16 bytes).
        ciphertext, tag = sealed[:-_TAG_LEN], sealed[-_TAG_LEN:]
        return WorkspaceEnvelope(
            algorithm=self.algorithm,
            key_ref=key_ref,
            encrypted_data_key=encrypted_data_key,
            nonce=nonce,
            ciphertext=ciphertext,
            tag=tag,
        )

    # ---------------------------------------------------------------- #
    # Opening                                                          #
    # ---------------------------------------------------------------- #

    def open(self, *, workspace: Workspace, envelope: WorkspaceEnvelope) -> bytes:
        key_ref = self._workspace_key_ref(workspace)
        if envelope.algorithm not in (self.algorithm, self.legacy_algorithm):
            raise WorkspaceEncryptionError("unsupported envelope algorithm")
        if not hmac.compare_digest(envelope.key_ref, key_ref):
            raise WorkspaceEncryptionError("envelope key_ref does not match workspace")
        try:
            data_key = self._kms.decrypt(
                key_ref=key_ref, ciphertext=envelope.encrypted_data_key
            )
        except KMSError as exc:
            raise WorkspaceEncryptionError("unable to unwrap workspace data key") from exc

        if envelope.algorithm == self.algorithm:
            return self._open_v2(data_key, key_ref, envelope)
        return self._open_v1(data_key, key_ref, envelope)

    # ---------------------------------------------------------------- #
    # v2 (AES-GCM)                                                     #
    # ---------------------------------------------------------------- #

    def _open_v2(
        self, data_key: bytes, key_ref: str, envelope: WorkspaceEnvelope
    ) -> bytes:
        if len(data_key) not in (16, 24, 32):
            data_key = hashlib.sha256(data_key).digest()
        if len(envelope.nonce) != _NONCE_LEN:
            raise WorkspaceEncryptionError("envelope authentication failed")
        if len(envelope.tag) != _TAG_LEN:
            raise WorkspaceEncryptionError("envelope authentication failed")
        try:
            return AESGCM(data_key).decrypt(
                envelope.nonce,
                envelope.ciphertext + envelope.tag,
                self._aad(key_ref),
            )
        except InvalidTag as exc:
            raise WorkspaceEncryptionError("envelope authentication failed") from exc
        except (TypeError, ValueError) as exc:
            raise WorkspaceEncryptionError("envelope authentication failed") from exc

    # ---------------------------------------------------------------- #
    # v1 legacy (XOR-stream + HMAC tag) — open only                    #
    # ---------------------------------------------------------------- #

    def _open_v1(
        self, data_key: bytes, key_ref: str, envelope: WorkspaceEnvelope
    ) -> bytes:
        expected = self._legacy_tag(
            data_key, key_ref, envelope.nonce, envelope.ciphertext
        )
        if not hmac.compare_digest(expected, envelope.tag):
            raise WorkspaceEncryptionError("envelope authentication failed")
        return self._legacy_xor(
            envelope.ciphertext,
            self._legacy_stream_key(data_key, envelope.nonce, len(envelope.ciphertext)),
        )

    # ---------------------------------------------------------------- #
    # Helpers                                                          #
    # ---------------------------------------------------------------- #

    @staticmethod
    def _aad(key_ref: str) -> bytes:
        """Authenticated additional data — binds ciphertext to the
        workspace's KMS key reference. Re-encryption to a different
        workspace fails authentication even with KMS access."""
        return b"loop.workspace-envelope:" + key_ref.encode("utf-8")

    @staticmethod
    def _workspace_key_ref(workspace: Workspace) -> str:
        if not workspace.tenant_kms_key_id:
            raise WorkspaceEncryptionError("workspace tenant_kms_key_id is required")
        return workspace.tenant_kms_key_id

    # legacy v1 helpers — preserved verbatim for migration window

    @staticmethod
    def _legacy_stream_key(data_key: bytes, nonce: bytes, length: int) -> bytes:
        out = b""
        counter = 0
        while len(out) < length:
            out += hashlib.sha256(
                data_key + nonce + counter.to_bytes(4, "big")
            ).digest()
            counter += 1
        return out[:length]

    @staticmethod
    def _legacy_tag(
        data_key: bytes, key_ref: str, nonce: bytes, ciphertext: bytes
    ) -> bytes:
        return hmac.new(
            data_key, key_ref.encode() + nonce + ciphertext, hashlib.sha256
        ).digest()

    @staticmethod
    def _legacy_xor(body: bytes, key: bytes) -> bytes:
        return bytes(
            byte ^ key[index % len(key)] for index, byte in enumerate(body)
        )


__all__ = [
    "WorkspaceEncryptionError",
    "WorkspaceEnvelope",
    "WorkspaceEnvelopeEncryption",
]
