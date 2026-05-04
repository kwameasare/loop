"""Runtime state for the cp-api app."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from loop_control_plane._app_agents import AgentRegistry, PostgresAgentRegistry
from loop_control_plane.agent_versions import AgentVersionService
from loop_control_plane.api_keys import ApiKeyService, PostgresApiKeyService
from loop_control_plane.api_keys_api import ApiKeyAPI
from loop_control_plane.audit_events import (
    AuditEventStore,
    InMemoryAuditEventStore,
    PostgresAuditEventStore,
)
from loop_control_plane.auth_exchange import (
    InMemoryRefreshTokenStore,
    PostgresRefreshTokenStore,
    RefreshTokenStore,
)
from loop_control_plane.budgets import BudgetService
from loop_control_plane.conversations import ConversationService
from loop_control_plane.data_deletion import (
    DataDeletionEmailNotifier,
    DataDeletionJobQueue,
    DataDeletionStore,
    InMemoryDataDeletionJobQueue,
    InMemoryDataDeletionStore,
    RecordingDataDeletionEmailNotifier,
)
from loop_control_plane.eval_suites import EvalSuiteService
from loop_control_plane.kb_documents import KbDocumentService
from loop_control_plane.saml import SamlValidator, StubSamlValidator
from loop_control_plane.secrets import InMemorySecretsBackend, SecretsBackend
from loop_control_plane.trace_search import (
    InMemoryTraceStore,
    TraceSearchService,
    TraceStore,
)
from loop_control_plane.usage import UsageLedger
from loop_control_plane.workspace_api import WorkspaceAPI
from loop_control_plane.workspaces import PostgresWorkspaceService, WorkspaceService


def _default_audit_event_store() -> AuditEventStore:
    """Pick between in-memory and Postgres-backed audit stores [P0.2].

    Wiring rule:

    * ``LOOP_CP_USE_POSTGRES=1`` AND ``LOOP_CP_DB_URL`` set →
      :class:`PostgresAuditEventStore` (production).
    * Otherwise → :class:`InMemoryAuditEventStore`. This keeps unit
      tests hermetic and lets air-gapped developer setups run cp-api
      without a database.
    """
    if os.environ.get("LOOP_CP_USE_POSTGRES") != "1":
        return InMemoryAuditEventStore()
    db_url = os.environ.get("LOOP_CP_DB_URL")
    if not db_url:
        # Fail closed: if the operator asked for Postgres but didn't
        # give us a URL, the audit trail would silently fall back to
        # in-memory (and lose every event on pod restart). Refuse to
        # start instead.
        raise RuntimeError(
            "LOOP_CP_USE_POSTGRES=1 requires LOOP_CP_DB_URL to be set"
        )
    return PostgresAuditEventStore.from_url(db_url)


def _default_refresh_token_store() -> RefreshTokenStore:
    """Pick between in-memory and Postgres-backed refresh-token stores [P0.2]."""
    if os.environ.get("LOOP_CP_USE_POSTGRES") != "1":
        return InMemoryRefreshTokenStore()
    db_url = os.environ.get("LOOP_CP_DB_URL")
    if not db_url:
        raise RuntimeError(
            "LOOP_CP_USE_POSTGRES=1 requires LOOP_CP_DB_URL to be set"
        )
    return PostgresRefreshTokenStore.from_url(db_url)


def _default_workspace_service() -> WorkspaceService | PostgresWorkspaceService:
    """Pick between in-memory and Postgres-backed workspace services [P0.2].

    Same env-var dispatch as the audit + refresh-token factories.
    The two return types share the async surface (create / get /
    list_for_user / add_member / role_of / list_members /
    remove_member / update_role / update / delete /
    require_same_region) so route handlers don't care which one is
    wired in.
    """
    if os.environ.get("LOOP_CP_USE_POSTGRES") != "1":
        return WorkspaceService()
    db_url = os.environ.get("LOOP_CP_DB_URL")
    if not db_url:
        raise RuntimeError(
            "LOOP_CP_USE_POSTGRES=1 requires LOOP_CP_DB_URL to be set"
        )
    return PostgresWorkspaceService.from_url(db_url)


def _default_agent_registry() -> AgentRegistry | PostgresAgentRegistry:
    """Pick between in-memory and Postgres-backed agent registries [P0.2]."""
    if os.environ.get("LOOP_CP_USE_POSTGRES") != "1":
        return AgentRegistry()
    db_url = os.environ.get("LOOP_CP_DB_URL")
    if not db_url:
        raise RuntimeError(
            "LOOP_CP_USE_POSTGRES=1 requires LOOP_CP_DB_URL to be set"
        )
    return PostgresAgentRegistry.from_url(db_url)


def _default_api_key_service() -> ApiKeyService | PostgresApiKeyService:
    """Pick between in-memory and Postgres-backed api-key services [P0.2]."""
    if os.environ.get("LOOP_CP_USE_POSTGRES") != "1":
        return ApiKeyService()
    db_url = os.environ.get("LOOP_CP_DB_URL")
    if not db_url:
        raise RuntimeError(
            "LOOP_CP_USE_POSTGRES=1 requires LOOP_CP_DB_URL to be set"
        )
    return PostgresApiKeyService.from_url(db_url)


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
    workspaces: WorkspaceService | PostgresWorkspaceService = field(
        default_factory=_default_workspace_service
    )
    audit_events: AuditEventStore = field(default_factory=_default_audit_event_store)
    agents: AgentRegistry | PostgresAgentRegistry = field(
        default_factory=_default_agent_registry
    )
    refresh_store: RefreshTokenStore = field(default_factory=_default_refresh_token_store)
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
    api_keys: ApiKeyService | PostgresApiKeyService = field(
        default_factory=_default_api_key_service
    )
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
    # P0.4 (KB documents):
    kb_documents: KbDocumentService = field(default_factory=KbDocumentService)
    # P0.4 (eval suites + runs):
    eval_suites: EvalSuiteService = field(default_factory=EvalSuiteService)

    def __post_init__(self) -> None:
        self.workspace_api = WorkspaceAPI(workspaces=self.workspaces)
        self.api_key_api = ApiKeyAPI(
            api_keys=self.api_keys, workspaces=self.workspaces
        )
        self.trace_search = TraceSearchService(self.trace_store)
        # P0.4: agent versions service depends on AgentRegistry; built
        # in __post_init__ so it shares the same agent storage map.
        self.agent_versions = AgentVersionService(self.agents)
