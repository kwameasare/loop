"""Agent versions service (P0.4).

Closes the agent-versions slice. The `agent_versions` table exists in
`cp_0001_initial.py`; this module provides the in-memory service
implementation with the same shape a Postgres-backed service will
expose. Used by `_routes_agent_versions.py`.

Versions are immutable: once created, an `AgentVersion` row never
changes. Promotion is a side-effect on the parent agent (it updates
``AgentRecord.active_version``). Rollback is a promotion to a prior
version number.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_agents import AgentRegistry, AgentRecord
from loop_control_plane.workspaces import WorkspaceError


class AgentVersionCreate(BaseModel):
    """Body for POST /v1/agents/{id}/versions."""

    model_config = ConfigDict(extra="forbid", strict=True)
    spec: dict[str, Any] = Field(default_factory=dict)
    """Free-form agent definition (system prompt, tools, model, etc.).
    The runtime applies it; cp persists the bytes verbatim and stamps
    a monotonically-increasing version number."""

    notes: str = Field(default="", max_length=2048)


class AgentVersion(BaseModel):
    """Stored representation. Immutable after creation."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: UUID
    workspace_id: UUID
    agent_id: UUID
    version: int = Field(ge=1)
    spec: dict[str, Any]
    notes: str
    created_at: datetime
    created_by: str = Field(min_length=1)


class AgentVersionError(ValueError):
    """Raised when version creation/promotion preconditions fail."""


class AgentVersionService:
    """Process-local versions store; production swaps in a Postgres-
    backed implementation against the `agent_versions` table."""

    def __init__(self, agents: AgentRegistry) -> None:
        self._agents = agents
        # (workspace_id, agent_id) -> [versions...]
        self._versions: dict[tuple[UUID, UUID], list[AgentVersion]] = {}
        self._lock = asyncio.Lock()

    async def list_for_agent(
        self, *, workspace_id: UUID, agent_id: UUID
    ) -> list[AgentVersion]:
        # Ensure the agent exists + belongs to the workspace.
        await self._agents.get(workspace_id=workspace_id, agent_id=agent_id)
        async with self._lock:
            rows = list(self._versions.get((workspace_id, agent_id), []))
            rows.sort(key=lambda v: v.version)
            return rows

    async def create(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        body: AgentVersionCreate,
        actor_sub: str,
    ) -> AgentVersion:
        # Ensure the agent exists.
        await self._agents.get(workspace_id=workspace_id, agent_id=agent_id)
        async with self._lock:
            existing = self._versions.setdefault((workspace_id, agent_id), [])
            next_version = (max((v.version for v in existing), default=0)) + 1
            row = AgentVersion(
                id=uuid4(),
                workspace_id=workspace_id,
                agent_id=agent_id,
                version=next_version,
                spec=body.spec,
                notes=body.notes,
                created_at=datetime.now(UTC),
                created_by=actor_sub,
            )
            existing.append(row)
            return row

    async def promote(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        version_id: UUID,
        actor_sub: str,
    ) -> AgentRecord:
        """Promote a version to the agent's active version. Idempotent:
        promoting the already-active version returns the unchanged agent."""
        agent = await self._agents.get(
            workspace_id=workspace_id, agent_id=agent_id
        )
        async with self._lock:
            versions = self._versions.get((workspace_id, agent_id), [])
            target = next((v for v in versions if v.id == version_id), None)
            if target is None:
                raise AgentVersionError(
                    f"unknown version: {version_id}"
                )
            if agent.active_version == target.version:
                return agent
            # Update the parent agent's active_version. We use
            # AgentRegistry's internal map directly because the
            # registry doesn't expose a public mutator yet — the
            # Postgres-backed service will issue an UPDATE.
            updated = agent.model_copy(update={"active_version": target.version})
            self._agents._agents[agent_id] = updated  # type: ignore[attr-defined]
            return updated


def _serialise_version(v: AgentVersion) -> dict[str, Any]:
    return {
        "id": str(v.id),
        "workspace_id": str(v.workspace_id),
        "agent_id": str(v.agent_id),
        "version": v.version,
        "spec": v.spec,
        "notes": v.notes,
        "created_at": v.created_at.isoformat(),
        "created_by": v.created_by,
    }


def _serialise_agent(agent: AgentRecord) -> dict[str, Any]:
    return {
        "id": str(agent.id),
        "workspace_id": str(agent.workspace_id),
        "name": agent.name,
        "slug": agent.slug,
        "description": agent.description,
        "active_version": agent.active_version,
        "created_at": agent.created_at.isoformat(),
    }


__all__ = [
    "AgentVersion",
    "AgentVersionCreate",
    "AgentVersionError",
    "AgentVersionService",
    "_serialise_agent",
    "_serialise_version",
]
