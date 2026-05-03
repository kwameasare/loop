from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass, field
from typing import Protocol

KMS_BACKENDS = ("aws_kms", "azure_key_vault", "gcp_kms", "alicloud_kms", "vault_transit")


class KMSError(RuntimeError): ...


class KMS(Protocol):
    backend: str

    def generate_data_key(self, *, key_ref: str) -> tuple[bytes, bytes]: ...
    def encrypt(self, *, key_ref: str, plaintext: bytes) -> bytes: ...
    def decrypt(self, *, key_ref: str, ciphertext: bytes) -> bytes: ...
    def rotate(self, *, key_ref: str) -> int: ...
    def sign(self, *, key_ref: str, payload: bytes) -> bytes: ...


@dataclass
class InMemoryKMS:
    backend: str
    _versions: dict[str, int] = field(default_factory=dict[str, int])

    def generate_data_key(self, *, key_ref: str) -> tuple[bytes, bytes]:
        material = self._material(key_ref, self._version(key_ref))
        plaintext = hashlib.sha256(material + b":data-key").digest()
        return plaintext, self.encrypt(key_ref=key_ref, plaintext=plaintext)

    def encrypt(self, *, key_ref: str, plaintext: bytes) -> bytes:
        version = self._version(key_ref)
        body = self._xor(plaintext, self._material(key_ref, version))
        packed = base64.urlsafe_b64encode(body).decode()
        return f"loopkms:{self.backend}:{version}:{packed}".encode()

    def decrypt(self, *, key_ref: str, ciphertext: bytes) -> bytes:
        try:
            prefix, backend, raw_version, packed = ciphertext.decode().split(":", 3)
        except ValueError as exc:
            raise KMSError("malformed ciphertext envelope") from exc
        if prefix != "loopkms" or backend != self.backend:
            raise KMSError("ciphertext backend mismatch")
        body = base64.urlsafe_b64decode(packed.encode())
        return self._xor(body, self._material(key_ref, int(raw_version)))

    def rotate(self, *, key_ref: str) -> int:
        self._versions[key_ref] = self._version(key_ref) + 1
        return self._versions[key_ref]

    def sign(self, *, key_ref: str, payload: bytes) -> bytes:
        key = self._material(key_ref, self._version(key_ref))
        return hmac.new(key, payload, hashlib.sha256).digest()

    def _version(self, key_ref: str) -> int:
        if not key_ref:
            raise KMSError("key_ref must be non-empty")
        return self._versions.get(key_ref, 1)

    def _material(self, key_ref: str, version: int) -> bytes:
        seed = f"{self.backend}:{key_ref}:{version}".encode()
        return hashlib.sha256(seed).digest()

    @staticmethod
    def _xor(body: bytes, key: bytes) -> bytes:
        return bytes(byte ^ key[index % len(key)] for index, byte in enumerate(body))


def build_kms_backend(backend: str, **kwargs: object) -> KMS:
    """Construct a KMS backend by name.

    The ``vault_transit`` backend dispatches to
    :func:`loop_control_plane.vault_transit.build_vault_transit_kms`
    when called with a ``config=VaultTransitConfig(...)`` kwarg. Without
    the kwarg we fall back to :class:`InMemoryKMS` so unit tests that
    don't care about real Vault still get a deterministic backend.

    Other named backends (``aws_kms``, ``azure_key_vault``, ``gcp_kms``,
    ``alicloud_kms``) currently use :class:`InMemoryKMS`; their real
    implementations land in S905 + follow-ups.
    """
    if backend not in KMS_BACKENDS:
        raise KMSError(f"unsupported KMS backend: {backend}")
    if backend == "vault_transit" and "config" in kwargs:
        # Lazy import — vault_transit.py imports hvac lazily inside its
        # own factory, but importing the module itself is free.
        from .vault_transit import VaultTransitConfig, build_vault_transit_kms

        config = kwargs["config"]
        if not isinstance(config, VaultTransitConfig):
            raise KMSError(
                f"vault_transit config must be a VaultTransitConfig; got "
                f"{type(config).__name__}"
            )
        client = kwargs.get("client")
        return build_vault_transit_kms(
            config,
            client=client,  # type: ignore[arg-type]
        )
    if backend == "aws_kms" and "config" in kwargs:
        # Lazy import — aws_backends.py imports boto3 lazily inside its
        # own factory, but importing the module itself is free.
        from .aws_backends import AwsKmsConfig, build_aws_kms_backend

        config = kwargs["config"]
        if not isinstance(config, AwsKmsConfig):
            raise KMSError(
                f"aws_kms config must be an AwsKmsConfig; got "
                f"{type(config).__name__}"
            )
        client = kwargs.get("client")
        return build_aws_kms_backend(
            config,
            client=client,  # type: ignore[arg-type]
        )
    return InMemoryKMS(backend=backend)
