from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

SECRETS_BACKENDS = (
    "vault",
    "aws_secrets_manager",
    "azure_key_vault",
    "gcp_secret_manager",
    "alicloud_kms_secret",
)


class SecretsBackendError(RuntimeError): ...


@dataclass(frozen=True)
class _SecretValue:
    value: str
    version: int


class SecretsBackend(Protocol):
    backend: str

    def set(self, ref: str, value: str, *, ttl_seconds: int | None = None) -> int: ...
    def get(self, ref: str) -> str: ...
    def rotate(self, ref: str, new_value: str) -> int: ...


@dataclass
class InMemorySecretsBackend:
    backend: str
    _secrets: dict[str, _SecretValue] = field(default_factory=dict[str, _SecretValue])

    def set(self, ref: str, value: str, *, ttl_seconds: int | None = None) -> int:
        self._validate_ref(ref)
        self._validate_value(value)
        if ttl_seconds is not None and ttl_seconds <= 0:
            raise SecretsBackendError("ttl_seconds must be positive")
        version = self._next_version(ref)
        self._secrets[ref] = _SecretValue(value=value, version=version)
        return version

    def get(self, ref: str) -> str:
        secret = self._secret(ref)
        return secret.value

    def rotate(self, ref: str, new_value: str) -> int:
        self._secret(ref)
        self._validate_value(new_value)
        version = self._next_version(ref)
        self._secrets[ref] = _SecretValue(value=new_value, version=version)
        return version

    def _secret(self, ref: str) -> _SecretValue:
        self._validate_ref(ref)
        if ref not in self._secrets:
            raise SecretsBackendError(f"{self.backend} secret not found: {ref}")
        return self._secrets[ref]

    def _next_version(self, ref: str) -> int:
        secret = self._secrets.get(ref)
        return 1 if secret is None else secret.version + 1

    @staticmethod
    def _validate_ref(ref: str) -> None:
        if not ref:
            raise SecretsBackendError("secret ref must be non-empty")

    @staticmethod
    def _validate_value(value: str) -> None:
        if not value:
            raise SecretsBackendError("secret value must be non-empty")


def build_secrets_backend(backend: str) -> SecretsBackend:
    if backend not in SECRETS_BACKENDS:
        raise SecretsBackendError(f"unsupported secrets backend: {backend}")
    return InMemorySecretsBackend(backend=backend)
