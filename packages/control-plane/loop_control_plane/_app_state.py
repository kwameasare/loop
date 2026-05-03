"""Runtime state for the cp-api app."""

from __future__ import annotations

from dataclasses import dataclass, field

from loop_control_plane._app_agents import AgentRegistry
from loop_control_plane.audit_events import InMemoryAuditEventStore
from loop_control_plane.auth_exchange import InMemoryRefreshTokenStore
from loop_control_plane.workspace_api import WorkspaceAPI
from loop_control_plane.workspaces import WorkspaceService


@dataclass
class CpApiState:
    workspaces: WorkspaceService = field(default_factory=WorkspaceService)
    audit_events: InMemoryAuditEventStore = field(default_factory=InMemoryAuditEventStore)
    agents: AgentRegistry = field(default_factory=AgentRegistry)
    refresh_store: InMemoryRefreshTokenStore = field(default_factory=InMemoryRefreshTokenStore)

    def __post_init__(self) -> None:
        self.workspace_api = WorkspaceAPI(workspaces=self.workspaces)
