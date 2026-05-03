from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane.workspaces import WorkspaceError


class AgentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=64)
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$", max_length=64)
    description: str = ""


class AgentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    workspace_id: UUID
    name: str
    slug: str
    description: str
    active_version: int | None = None
    created_at: datetime
    archived_at: datetime | None = None


class AgentRegistry:
    """Process-local agent registry until the Postgres facade lands."""

    def __init__(self) -> None:
        self._agents: dict[UUID, AgentRecord] = {}
        self._lock = asyncio.Lock()

    async def create(self, *, workspace_id: UUID, body: AgentCreate) -> AgentRecord:
        async with self._lock:
            if any(
                a.workspace_id == workspace_id and a.slug == body.slug and a.archived_at is None
                for a in self._agents.values()
            ):
                raise WorkspaceError(f"agent slug already taken: {body.slug}")
            agent = AgentRecord(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                name=body.name,
                slug=body.slug,
                description=body.description,
                created_at=datetime.now(UTC),
            )
            self._agents[agent.id] = agent
            return agent

    async def list_for_workspace(self, workspace_id: UUID) -> list[AgentRecord]:
        async with self._lock:
            rows = [
                a
                for a in self._agents.values()
                if a.workspace_id == workspace_id and a.archived_at is None
            ]
            return sorted(rows, key=lambda a: a.created_at)

    async def get(self, *, workspace_id: UUID, agent_id: UUID) -> AgentRecord:
        async with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None or agent.workspace_id != workspace_id or agent.archived_at is not None:
                raise WorkspaceError(f"unknown agent: {agent_id}")
            return agent

    async def archive(self, *, workspace_id: UUID, agent_id: UUID) -> None:
        async with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None or agent.workspace_id != workspace_id or agent.archived_at is not None:
                raise WorkspaceError(f"unknown agent: {agent_id}")
            self._agents[agent_id] = agent.model_copy(update={"archived_at": datetime.now(UTC)})


def agent_payload(agent: AgentRecord) -> dict[str, Any]:
    return agent.model_dump(mode="json", exclude={"archived_at"})
