"""BYO (Bring-Your-Own) Vault integration — S637.

Allows enterprise tenants to point Loop at *their* HashiCorp Vault
cluster instead of Loop's managed Vault. Per-workspace configuration
captures the vault address, the auth role, and the optional Vault
namespace + KV mount path. Loop authenticates to the customer's Vault
using AppRole (role_id is configured here, secret_id is fetched at
runtime via the customer's response-wrapping flow — outside the scope
of this module).

Public API:

* :class:`VaultConfig` — frozen dataclass: address + role + namespace +
  mount_path.
* :class:`ByoVaultStore` Protocol + :class:`InMemoryByoVaultStore`.
* :class:`ByoVaultClient` Protocol — production wires to ``hvac``;
  tests wire to :class:`StubByoVaultClient` which replays a fixture map.
* :func:`fetch_secret` — workspace-scoped secret fetch.

Companion: ``loop_implementation/engineering/RUNBOOKS.md`` RB-024
(BYO Vault credential rotation).
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

__all__ = [
    "ByoVaultClient",
    "ByoVaultError",
    "ByoVaultStore",
    "InMemoryByoVaultStore",
    "StubByoVaultClient",
    "VaultConfig",
    "fetch_secret",
]


_ROLE_PATTERN = re.compile(r"^[A-Za-z0-9._\-]{1,128}$")


class ByoVaultError(ValueError):
    """Raised for invalid configs or missing secrets."""


@dataclass(frozen=True, slots=True)
class VaultConfig:
    """Per-workspace BYO Vault configuration.

    ``address`` must be an https URL. Vault namespace + KV mount path
    default to the canonical values used by HashiCorp Vault Enterprise.
    """

    workspace_id: uuid.UUID
    address: str
    role: str
    namespace: str | None = None
    mount_path: str = "secret"

    def __post_init__(self) -> None:
        url = urlparse(self.address)
        if url.scheme not in ("https",):
            raise ByoVaultError(
                f"address must be an https URL, got {self.address!r}"
            )
        if not url.netloc:
            raise ByoVaultError(f"address has no host: {self.address!r}")
        if not _ROLE_PATTERN.match(self.role):
            raise ByoVaultError(
                f"role must match {_ROLE_PATTERN.pattern}, got {self.role!r}"
            )
        if not self.mount_path or self.mount_path.startswith("/"):
            raise ByoVaultError(
                f"mount_path must be non-empty and not start with /, "
                f"got {self.mount_path!r}"
            )
        if self.namespace is not None and not self.namespace.strip():
            raise ByoVaultError("namespace must be None or a non-blank string")


class ByoVaultStore(Protocol):
    def upsert(self, config: VaultConfig) -> None: ...
    def get(self, workspace_id: uuid.UUID) -> VaultConfig | None: ...
    def delete(self, workspace_id: uuid.UUID) -> bool: ...


class ByoVaultClient(Protocol):
    """Read-only seam over the customer's Vault. Production: hvac client."""

    def read_kv2(
        self,
        *,
        address: str,
        role: str,
        namespace: str | None,
        mount_path: str,
        path: str,
    ) -> Mapping[str, str]: ...


class InMemoryByoVaultStore:
    def __init__(self) -> None:
        self._rows: dict[uuid.UUID, VaultConfig] = {}

    def upsert(self, config: VaultConfig) -> None:
        self._rows[config.workspace_id] = config

    def get(self, workspace_id: uuid.UUID) -> VaultConfig | None:
        return self._rows.get(workspace_id)

    def delete(self, workspace_id: uuid.UUID) -> bool:
        return self._rows.pop(workspace_id, None) is not None


class StubByoVaultClient:
    """Test client. Stores secrets keyed by (address, mount_path, path).

    Records every read so tests can assert that the correct address/role
    were used for the workspace under test.
    """

    def __init__(
        self,
        secrets: Mapping[tuple[str, str, str], Mapping[str, str]] | None = None,
    ) -> None:
        self.secrets: dict[
            tuple[str, str, str], Mapping[str, str]
        ] = dict(secrets or {})
        self.reads: list[
            tuple[str, str, str | None, str, str]
        ] = []  # (address, role, namespace, mount_path, path)

    def read_kv2(
        self,
        *,
        address: str,
        role: str,
        namespace: str | None,
        mount_path: str,
        path: str,
    ) -> Mapping[str, str]:
        self.reads.append((address, role, namespace, mount_path, path))
        key = (address, mount_path, path)
        if key not in self.secrets:
            raise ByoVaultError(
                f"secret not found at {mount_path}/{path} on {address}"
            )
        return self.secrets[key]


def fetch_secret(
    *,
    workspace_id: uuid.UUID,
    path: str,
    store: ByoVaultStore,
    client: ByoVaultClient,
) -> Mapping[str, str]:
    """Fetch a KV-v2 secret from the workspace's BYO Vault.

    Raises :class:`ByoVaultError` if the workspace has no BYO Vault
    config or the secret is missing.
    """
    if not path or path.startswith("/"):
        raise ByoVaultError("path must be non-empty and not start with /")
    config = store.get(workspace_id)
    if config is None:
        raise ByoVaultError(
            f"workspace {workspace_id} has no BYO Vault config"
        )
    return client.read_kv2(
        address=config.address,
        role=config.role,
        namespace=config.namespace,
        mount_path=config.mount_path,
        path=path,
    )
