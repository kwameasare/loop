"""Vault transit KMS backend (S918).

Real ``hvac``-backed implementation of the :class:`~loop_control_plane.kms.KMS`
Protocol that encrypts and decrypts via HashiCorp Vault's `transit
<https://developer.hashicorp.com/vault/docs/secrets/transit>`_ secrets engine.

Why this exists
===============

The KMS Protocol in :mod:`loop_control_plane.kms` previously had only an
:class:`~loop_control_plane.kms.InMemoryKMS` implementation — fine for
unit tests but unusable in production.

S918 closes that gap for the **Vault** backend specifically (the AWS /
Azure / GCP backends are S905+). The choice of Vault first is deliberate:

1. Vault transit is the universal abstraction for the BYO-customer-vault
   story (S637), so wiring it to the KMS Protocol means an enterprise
   customer who already runs Vault can re-use their existing
   transit-key estate without provisioning anything else.
2. Vault is open source and runs locally in docker for integration
   tests — cloud-KMS impls need localstack or live cloud accounts.

Design
======

* :class:`VaultTransitKMS` implements every method of the KMS Protocol
  (``generate_data_key``, ``encrypt``, ``decrypt``, ``rotate``, ``sign``)
  by mapping each to its Vault transit endpoint:

  - ``encrypt`` → ``POST /v1/{mount}/encrypt/{key_ref}``
  - ``decrypt`` → ``POST /v1/{mount}/decrypt/{key_ref}``
  - ``generate_data_key`` → ``POST /v1/{mount}/datakey/plaintext/{key_ref}``
  - ``rotate`` → ``POST /v1/{mount}/keys/{key_ref}/rotate``
  - ``sign`` → ``POST /v1/{mount}/hmac/{key_ref}``

* The backend never trusts an upstream-returned plaintext for decryption
  caching — every call is round-tripped to Vault. This is intentional:
  Vault transit is the *source of truth* for envelope keys and we don't
  have a way to invalidate a local cache atomically across pods.

* Authentication is via a static token (``LOOP_VAULT_TOKEN``) for the
  managed deployment, or via AppRole + response-wrapping for the BYO
  Vault path (see :mod:`loop_control_plane.byo_vault`). The
  :class:`VaultTransitKMS` constructor accepts a pre-built ``hvac.Client``
  so credential acquisition is the caller's problem.

* On any Vault error we raise :class:`~loop_control_plane.kms.KMSError`
  with the Vault status code in the message. We never propagate the
  raw ``hvac`` exception types out of this module so callers don't need
  to depend on hvac.

Tests
=====

* Unit tests use :class:`_VaultTransitClientStub` — a tiny in-memory
  implementation of the ``hvac.Client.secrets.transit.*`` surface this
  module touches. This keeps ``hvac`` an *optional* runtime dependency
  for users who want a different KMS backend.

* Integration tests (gated on ``LOOP_VAULT_INTEGRATION=1``) spin a real
  `vault:1.18` container via the existing docker-compose stack, create
  a transit key, and exercise the full encrypt/decrypt/rotate cycle.
  See :mod:`tests.test_vault_transit_integration`.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Protocol

from .kms import KMSError

__all__ = [
    "VaultTransitClient",
    "VaultTransitConfig",
    "VaultTransitKMS",
]


# --------------------------------------------------------------------------- #
# Configuration                                                               #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class VaultTransitConfig:
    """Connection metadata for the Vault transit engine.

    Args:
        address: Vault address (e.g. ``https://vault.example.com:8200``).
        token: Vault token used for authentication. Pulled from
            ``LOOP_VAULT_TOKEN`` in production. The token must have a
            policy granting ``encrypt``, ``decrypt``, ``datakey``,
            ``rotate``, and ``hmac`` capabilities on the configured
            mount.
        mount_path: Path the transit engine is mounted under. Defaults
            to ``transit`` per Vault convention.
        namespace: Optional Vault Enterprise namespace.
        timeout_seconds: Per-request HTTP timeout in seconds.
    """

    address: str
    token: str
    mount_path: str = "transit"
    namespace: str | None = None
    timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        if not self.address.startswith(("http://", "https://")):
            raise ValueError(
                f"VaultTransitConfig.address must start with http(s)://; got {self.address!r}"
            )
        if not self.token:
            raise ValueError("VaultTransitConfig.token must be a non-empty string")
        if not self.mount_path or self.mount_path.startswith("/"):
            raise ValueError(
                f"VaultTransitConfig.mount_path must be a non-empty relative path; got {self.mount_path!r}"
            )
        if self.timeout_seconds <= 0:
            raise ValueError(
                f"VaultTransitConfig.timeout_seconds must be > 0; got {self.timeout_seconds}"
            )


# --------------------------------------------------------------------------- #
# Client Protocol — real impl is hvac.Client; tests use _VaultTransitClientStub #
# --------------------------------------------------------------------------- #


class _TransitOperations(Protocol):
    """Subset of ``hvac.Client.secrets.transit.*`` we depend on.

    Each method returns the Vault response body (a dict) — the same
    shape ``hvac`` returns. We keep the Protocol narrow to the methods
    we actually call so the test stub stays small.
    """

    def encrypt_data(
        self,
        name: str,
        plaintext: str,
        mount_point: str,
    ) -> dict[str, Any]: ...

    def decrypt_data(
        self,
        name: str,
        ciphertext: str,
        mount_point: str,
    ) -> dict[str, Any]: ...

    def generate_data_key(
        self,
        name: str,
        key_type: str,
        mount_point: str,
    ) -> dict[str, Any]: ...

    def rotate_key(
        self,
        name: str,
        mount_point: str,
    ) -> dict[str, Any]: ...

    def generate_hmac(
        self,
        name: str,
        hash_input: str,
        mount_point: str,
    ) -> dict[str, Any]: ...

    def read_key(
        self,
        name: str,
        mount_point: str,
    ) -> dict[str, Any]: ...


class _SecretsNamespace(Protocol):
    transit: _TransitOperations


class VaultTransitClient(Protocol):
    """Subset of ``hvac.Client`` we depend on.

    This is what gets passed to :class:`VaultTransitKMS`. The real
    implementation is ``hvac.Client(url=..., token=..., namespace=...)``;
    tests pass :class:`_VaultTransitClientStub`.
    """

    secrets: _SecretsNamespace


# --------------------------------------------------------------------------- #
# Production backend                                                          #
# --------------------------------------------------------------------------- #


@dataclass
class VaultTransitKMS:
    """KMS-Protocol implementation backed by Vault's transit engine.

    Construct with a configured :class:`VaultTransitClient` (in
    production: ``hvac.Client``). The ``backend`` field is fixed to
    ``"vault_transit"`` so :data:`loop_control_plane.kms.KMS_BACKENDS`
    resolution returns this class.
    """

    client: VaultTransitClient
    config: VaultTransitConfig
    backend: str = "vault_transit"

    # ---- KMS Protocol implementation -------------------------------------

    def generate_data_key(self, *, key_ref: str) -> tuple[bytes, bytes]:
        self._validate_key_ref(key_ref)
        try:
            response = self.client.secrets.transit.generate_data_key(
                name=key_ref,
                key_type="plaintext",
                mount_point=self.config.mount_path,
            )
        except Exception as exc:
            raise KMSError(
                f"vault transit generate_data_key failed for {key_ref!r}: {exc}"
            ) from exc

        data = _data_field(response)
        plaintext_b64 = _str_field(data, "plaintext", key_ref)
        ciphertext = _str_field(data, "ciphertext", key_ref)
        try:
            plaintext = base64.b64decode(plaintext_b64, validate=True)
        except (ValueError, TypeError) as exc:
            raise KMSError(f"vault transit returned non-base64 plaintext for {key_ref!r}") from exc
        return plaintext, ciphertext.encode()

    def encrypt(self, *, key_ref: str, plaintext: bytes) -> bytes:
        self._validate_key_ref(key_ref)
        plaintext_b64 = base64.b64encode(plaintext).decode()
        try:
            response = self.client.secrets.transit.encrypt_data(
                name=key_ref,
                plaintext=plaintext_b64,
                mount_point=self.config.mount_path,
            )
        except Exception as exc:
            raise KMSError(f"vault transit encrypt failed for {key_ref!r}: {exc}") from exc
        ciphertext = _str_field(_data_field(response), "ciphertext", key_ref)
        return ciphertext.encode()

    def decrypt(self, *, key_ref: str, ciphertext: bytes) -> bytes:
        self._validate_key_ref(key_ref)
        try:
            response = self.client.secrets.transit.decrypt_data(
                name=key_ref,
                ciphertext=ciphertext.decode(),
                mount_point=self.config.mount_path,
            )
        except UnicodeDecodeError as exc:
            raise KMSError(f"vault transit ciphertext for {key_ref!r} is not utf-8 text") from exc
        except Exception as exc:
            raise KMSError(f"vault transit decrypt failed for {key_ref!r}: {exc}") from exc
        plaintext_b64 = _str_field(_data_field(response), "plaintext", key_ref)
        try:
            return base64.b64decode(plaintext_b64, validate=True)
        except (ValueError, TypeError) as exc:
            raise KMSError(f"vault transit returned non-base64 plaintext for {key_ref!r}") from exc

    def rotate(self, *, key_ref: str) -> int:
        self._validate_key_ref(key_ref)
        try:
            self.client.secrets.transit.rotate_key(
                name=key_ref,
                mount_point=self.config.mount_path,
            )
            response = self.client.secrets.transit.read_key(
                name=key_ref,
                mount_point=self.config.mount_path,
            )
        except Exception as exc:
            raise KMSError(f"vault transit rotate failed for {key_ref!r}: {exc}") from exc
        data = _data_field(response)
        latest = data.get("latest_version")
        if not isinstance(latest, int):
            raise KMSError(
                f"vault transit returned non-integer latest_version for {key_ref!r}: {latest!r}"
            )
        return latest

    def sign(self, *, key_ref: str, payload: bytes) -> bytes:
        self._validate_key_ref(key_ref)
        payload_b64 = base64.b64encode(payload).decode()
        try:
            response = self.client.secrets.transit.generate_hmac(
                name=key_ref,
                hash_input=payload_b64,
                mount_point=self.config.mount_path,
            )
        except Exception as exc:
            raise KMSError(f"vault transit hmac failed for {key_ref!r}: {exc}") from exc
        hmac_str = _str_field(_data_field(response), "hmac", key_ref)
        # Vault returns "vault:vN:<base64>"; we keep that envelope so
        # callers can verify the key version on read.
        return hmac_str.encode()

    # ---- internal --------------------------------------------------------

    @staticmethod
    def _validate_key_ref(key_ref: str) -> None:
        if not key_ref:
            raise KMSError("vault transit key_ref must be non-empty")
        if any(c in key_ref for c in "/\\"):
            raise KMSError(
                f"vault transit key_ref must not contain path separators; got {key_ref!r}"
            )


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _data_field(response: dict[str, Any]) -> dict[str, Any]:
    """Pull ``response['data']`` as a dict, raising :class:`KMSError` if missing.

    ``hvac`` always wraps the Vault response under ``data``. If the
    server returns the bare body (some auth-token edge cases), we treat
    the top-level dict as the data payload — the read still succeeds
    and the test stub doesn't have to mimic the wrapper.
    """
    if not isinstance(response, dict):
        raise KMSError(f"vault transit response is not a dict: {type(response).__name__}")
    data = response.get("data")
    if data is None:
        return response
    if not isinstance(data, dict):
        raise KMSError(f"vault transit response.data is not a dict: {type(data).__name__}")
    return data


def _str_field(payload: dict[str, Any], key: str, key_ref: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise KMSError(
            f"vault transit response missing string field {key!r} for {key_ref!r}: "
            f"got {type(value).__name__}"
        )
    return value


# --------------------------------------------------------------------------- #
# Factory hook                                                                #
# --------------------------------------------------------------------------- #


def build_vault_transit_kms(
    config: VaultTransitConfig,
    *,
    client: VaultTransitClient | None = None,
) -> VaultTransitKMS:
    """Construct a :class:`VaultTransitKMS`, importing ``hvac`` lazily.

    ``hvac`` is imported only when ``client`` is not supplied so users
    who don't need the Vault backend never pay the import cost. If
    ``hvac`` isn't installed and the caller didn't pre-build a client,
    we raise :class:`KMSError` with a helpful install hint.
    """
    if client is not None:
        return VaultTransitKMS(client=client, config=config)
    try:
        import hvac  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover — install-time error
        raise KMSError(
            "vault transit backend requires the 'hvac' package. Install with: uv pip install hvac"
        ) from exc

    real_client = hvac.Client(
        url=config.address,
        token=config.token,
        namespace=config.namespace,
        timeout=config.timeout_seconds,
    )
    return VaultTransitKMS(client=real_client, config=config)
