"""Runtime state for the cp-api app."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from loop_control_plane._app_agents import AgentRegistry
from loop_control_plane.audit_events import InMemoryAuditEventStore
from loop_control_plane.auth_exchange import InMemoryRefreshTokenStore
from loop_control_plane.data_deletion import (
    DataDeletionEmailNotifier,
    DataDeletionJobQueue,
    DataDeletionStore,
    InMemoryDataDeletionJobQueue,
    InMemoryDataDeletionStore,
    RecordingDataDeletionEmailNotifier,
)
from loop_control_plane.saml import SamlValidator, StubSamlValidator
from loop_control_plane.workspace_api import WorkspaceAPI
from loop_control_plane.workspaces import WorkspaceService


def _default_saml_validator() -> SamlValidator:
    """Pick between Stub and PySAML2 validators per ``LOOP_SAML_USE_PYSAML2``.

    Default: :class:`StubSamlValidator` (sandbox-tenant-only). Setting
    ``LOOP_SAML_USE_PYSAML2=1`` switches to the real
    :class:`PySAML2Validator` (S917). The PySAML2 import is lazy — if
    the package isn't installed and the env var demands it, we raise
    at startup with a clear install hint rather than at first request.
    """
    if os.environ.get("LOOP_SAML_USE_PYSAML2") != "1":
        return StubSamlValidator()
    # Lazy import — pysaml2 is an optional extra.
    from loop_control_plane.saml_pysaml2 import build_pysaml2_validator

    require_response_signature = os.environ.get("LOOP_SAML_REQUIRE_RESPONSE_SIGNATURE", "1") == "1"
    return build_pysaml2_validator(
        require_response_signature=require_response_signature,
    )


@dataclass
class CpApiState:
    workspaces: WorkspaceService = field(default_factory=WorkspaceService)
    audit_events: InMemoryAuditEventStore = field(default_factory=InMemoryAuditEventStore)
    agents: AgentRegistry = field(default_factory=AgentRegistry)
    refresh_store: InMemoryRefreshTokenStore = field(default_factory=InMemoryRefreshTokenStore)
    saml_validator: SamlValidator = field(default_factory=_default_saml_validator)
    # P0.8b: GDPR DSR (Data Subject Request) infra. Default impls are
    # in-memory + recording for dev/tests; production wires Postgres-
    # backed store + a real job queue + an email transport.
    data_deletion_store: DataDeletionStore = field(
        default_factory=InMemoryDataDeletionStore
    )
    data_deletion_queue: DataDeletionJobQueue = field(
        default_factory=InMemoryDataDeletionJobQueue
    )
    data_deletion_notifier: DataDeletionEmailNotifier = field(
        default_factory=RecordingDataDeletionEmailNotifier
    )

    def __post_init__(self) -> None:
        self.workspace_api = WorkspaceAPI(workspaces=self.workspaces)
