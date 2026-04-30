"""BYO-key resolution (S708, replaces S510 in pass9 slate).

Workspaces can attach their own provider API keys (OpenAI, Anthropic,
Voyage, Cohere, ...) to escape Loop's pass-through markup or hit a
custom endpoint. Keys are stored encrypted by the control-plane in
``workspace_keys``; the gateway resolves them per-request via this
module.

Resolution rules (deterministic, documented in HANDBOOK):

1. If the workspace has a key for the *exact* concrete model
   (e.g. ``gpt-4o-mini``), use it.
2. Otherwise if it has a key for the model's *vendor*
   (``openai`` / ``anthropic`` / ``voyage``), use it.
3. Otherwise fall back to the platform default (``LOOP_*`` env keys),
   which the caller may opt to forbid (raises ``BYOKeyMissing``).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable
from uuid import UUID


class Vendor(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    VOYAGE = "voyage"
    COHERE = "cohere"
    MISTRAL = "mistral"
    GOOGLE = "google"


_MODEL_VENDOR_PREFIXES: tuple[tuple[str, Vendor], ...] = (
    ("gpt-", Vendor.OPENAI),
    ("o1-", Vendor.OPENAI),
    ("o3-", Vendor.OPENAI),
    ("text-embedding-", Vendor.OPENAI),
    ("claude-", Vendor.ANTHROPIC),
    ("voyage-", Vendor.VOYAGE),
    ("rerank-", Vendor.COHERE),
    ("command-", Vendor.COHERE),
    ("mistral-", Vendor.MISTRAL),
    ("codestral-", Vendor.MISTRAL),
    ("gemini-", Vendor.GOOGLE),
)


def vendor_for_model(model: str) -> Vendor:
    """Best-effort vendor inference from a model name."""
    for prefix, vendor in _MODEL_VENDOR_PREFIXES:
        if model.startswith(prefix):
            return vendor
    raise KeyError(f"cannot infer vendor for model {model!r}")


class BYOKeyMissing(LookupError):  # noqa: N818
    """The workspace requires BYO-key but none is configured."""


@dataclass(frozen=True, slots=True)
class ResolvedKey:
    """A resolved API key with provenance."""

    api_key: str
    source: str  # "workspace_model" | "workspace_vendor" | "platform_default"


@runtime_checkable
class WorkspaceKeyStore(Protocol):
    """Read-only view over the encrypted ``workspace_keys`` table."""

    def get_for_model(self, workspace_id: UUID, model: str) -> str | None: ...

    def get_for_vendor(self, workspace_id: UUID, vendor: Vendor) -> str | None: ...


@dataclass(slots=True)
class InMemoryWorkspaceKeyStore:
    """Test double for ``WorkspaceKeyStore``.

    Production wires the same Protocol against the control-plane DB.
    """

    by_model: dict[tuple[UUID, str], str]
    by_vendor: dict[tuple[UUID, Vendor], str]

    def __init__(self) -> None:
        self.by_model = {}
        self.by_vendor = {}

    def set_model_key(self, workspace_id: UUID, model: str, api_key: str) -> None:
        self.by_model[(workspace_id, model)] = api_key

    def set_vendor_key(self, workspace_id: UUID, vendor: Vendor, api_key: str) -> None:
        self.by_vendor[(workspace_id, vendor)] = api_key

    def get_for_model(self, workspace_id: UUID, model: str) -> str | None:
        return self.by_model.get((workspace_id, model))

    def get_for_vendor(self, workspace_id: UUID, vendor: Vendor) -> str | None:
        return self.by_vendor.get((workspace_id, vendor))


class WorkspaceKeyResolver:
    """Apply the BYO-key resolution rules."""

    def __init__(
        self,
        store: WorkspaceKeyStore,
        *,
        platform_defaults: dict[Vendor, str] | None = None,
        require_byo: bool = False,
    ) -> None:
        self._store = store
        self._defaults = dict(platform_defaults or {})
        self._require_byo = require_byo

    def resolve(self, *, workspace_id: UUID, model: str) -> ResolvedKey:
        per_model = self._store.get_for_model(workspace_id, model)
        if per_model:
            return ResolvedKey(api_key=per_model, source="workspace_model")
        try:
            vendor = vendor_for_model(model)
        except KeyError:
            vendor = None  # type: ignore[assignment]
        if vendor is not None:
            per_vendor = self._store.get_for_vendor(workspace_id, vendor)
            if per_vendor:
                return ResolvedKey(api_key=per_vendor, source="workspace_vendor")
            default = self._defaults.get(vendor)
        else:
            default = None
        if default and not self._require_byo:
            return ResolvedKey(api_key=default, source="platform_default")
        raise BYOKeyMissing(
            f"no BYO key for workspace {workspace_id} model {model!r}; "
            "and platform default is unavailable or forbidden"
        )


__all__ = [
    "BYOKeyMissing",
    "InMemoryWorkspaceKeyStore",
    "ResolvedKey",
    "Vendor",
    "WorkspaceKeyResolver",
    "WorkspaceKeyStore",
    "vendor_for_model",
]
