"""Runtime state for the cp-api app."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from loop_control_plane._app_agents import AgentRegistry
from loop_control_plane.agent_versions import AgentVersionService
from loop_control_plane.api_keys import ApiKeyService
from loop_control_plane.api_keys_api import ApiKeyAPI
from loop_control_plane.budgets import BudgetService
from loop_control_plane.conversations import ConversationService
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
from loop_control_plane.secrets import InMemorySecretsBackend, SecretsBackend
from loop_control_plane.trace_search import (
    InMemoryTraceStore,
    TraceSearchService,
    TraceStore,
)
from loop_control_plane.usage import UsageLedger, UsageRollup
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
    # P0.4 (api-keys + secrets):
    api_keys: ApiKeyService = field(default_factory=ApiKeyService)
    secrets_backend: SecretsBackend = field(
        default_factory=lambda: InMemorySecretsBackend(backend="loop-dev")
    )
    # P0.4 (traces + usage):
    trace_store: TraceStore = field(default_factory=InMemoryTraceStore)
    usage_ledger: UsageLedger = field(default_factory=UsageLedger)
    # P0.4 (conversations + takeover):
    conversations: ConversationService = field(default_factory=ConversationService)
    # P0.4 (budgets):
    budgets: BudgetService = field(default_factory=BudgetService)

    def __post_init__(self) -> None:
        self.workspace_api = WorkspaceAPI(workspaces=self.workspaces)
        self.api_key_api = ApiKeyAPI(
            api_keys=self.api_keys, workspaces=self.workspaces
        )
        self.trace_search = TraceSearchService(self.trace_store)
        # P0.4: agent versions service depends on AgentRegistry; built
        # in __post_init__ so it shares the same agent storage map.
        self.agent_versions = AgentVersionService(self.agents)
