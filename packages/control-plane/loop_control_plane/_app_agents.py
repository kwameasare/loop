from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane.workspaces import WorkspaceError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


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


# ---------------------------------------------------------------------------
# Postgres-backed registry [P0.2]
# ---------------------------------------------------------------------------


class PostgresAgentRegistry:
    """Postgres-backed agent registry — drop-in for :class:`AgentRegistry`.

    Same async surface (``create / list_for_workspace / get /
    archive``), same :class:`AgentRecord` return type, same
    :class:`WorkspaceError` failure mode.

    Schema lives in ``cp_0001_initial`` (agents) +
    ``cp_0010_agents_align`` (rename ``display_name`` → ``name``, add
    ``description``). The ``current_version_id`` column from cp_0001
    is left as opaque NULL — :class:`AgentRecord.active_version` is
    ``int | None`` while the column is UUID, so the two don't map
    cleanly. The in-memory registry never sets ``active_version``
    either, so this is a no-op divergence today; a future agent-
    versions service can decide how to bridge them.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @classmethod
    def from_url(cls, database_url: str, *, echo: bool = False) -> PostgresAgentRegistry:
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(
            database_url,
            echo=echo,
            future=True,
            pool_pre_ping=True,
        )
        return cls(engine)

    async def create(self, *, workspace_id: UUID, body: AgentCreate) -> AgentRecord:
        from sqlalchemy import text
        from sqlalchemy.exc import IntegrityError

        new_id = uuid.uuid4()
        now = datetime.now(UTC)
        try:
            async with self._engine.begin() as conn:
                await _set_rls_workspace(conn, workspace_id)
                await conn.execute(
                    text(
                        """
                        INSERT INTO agents (
                            id, workspace_id, name, slug, description,
                            created_at
                        ) VALUES (
                            :id, :workspace_id, :name, :slug, :description,
                            :created_at
                        )
                        """
                    ),
                    {
                        "id": new_id,
                        "workspace_id": workspace_id,
                        "name": body.name,
                        "slug": body.slug,
                        "description": body.description,
                        "created_at": now,
                    },
                )
        except IntegrityError as exc:
            # The unique (workspace_id, slug) constraint fires here;
            # also fires if the workspace doesn't exist (FK
            # violation). Both surface as WorkspaceError to match the
            # in-memory contract.
            raise WorkspaceError(f"agent slug already taken: {body.slug}") from exc
        return AgentRecord(
            id=new_id,
            workspace_id=workspace_id,
            name=body.name,
            slug=body.slug,
            description=body.description,
            created_at=now,
        )

    async def list_for_workspace(
        self, workspace_id: UUID
    ) -> list[AgentRecord]:
        from sqlalchemy import text

        async with self._engine.begin() as conn:
            await _set_rls_workspace(conn, workspace_id)
            rows = (
                await conn.execute(
                    text(
                        """
                        SELECT id, workspace_id, name, slug, description,
                               created_at, archived_at
                          FROM agents
                         WHERE workspace_id = :workspace_id
                           AND archived_at IS NULL
                         ORDER BY created_at ASC
                        """
                    ),
                    {"workspace_id": workspace_id},
                )
            ).all()
        return [_row_to_agent(row) for row in rows]

    async def get(self, *, workspace_id: UUID, agent_id: UUID) -> AgentRecord:
        from sqlalchemy import text

        async with self._engine.begin() as conn:
            await _set_rls_workspace(conn, workspace_id)
            row = (
                await conn.execute(
                    text(
                        """
                        SELECT id, workspace_id, name, slug, description,
                               created_at, archived_at
                          FROM agents
                         WHERE id = :id
                           AND workspace_id = :workspace_id
                           AND archived_at IS NULL
                        """
                    ),
                    {"id": agent_id, "workspace_id": workspace_id},
                )
            ).first()
        if row is None:
            raise WorkspaceError(f"unknown agent: {agent_id}")
        return _row_to_agent(row)

    async def archive(self, *, workspace_id: UUID, agent_id: UUID) -> None:
        from sqlalchemy import text

        async with self._engine.begin() as conn:
            await _set_rls_workspace(conn, workspace_id)
            result = await conn.execute(
                text(
                    """
                    UPDATE agents
                       SET archived_at = :archived_at
                     WHERE id = :id
                       AND workspace_id = :workspace_id
                       AND archived_at IS NULL
                    """
                ),
                {
                    "archived_at": datetime.now(UTC),
                    "id": agent_id,
                    "workspace_id": workspace_id,
                },
            )
            if result.rowcount == 0:
                raise WorkspaceError(f"unknown agent: {agent_id}")


async def _set_rls_workspace(conn: object, workspace_id: UUID) -> None:
    """Set the ``loop.workspace_id`` GUC inside the active transaction.

    The cp_0001 RLS policies on ``agents`` (and friends) read this
    setting via ``current_setting('loop.workspace_id', true)::uuid``;
    without it, every INSERT/SELECT/UPDATE returns InsufficientPrivilege.
    Set it on every transaction — connection pooling means a connection
    handed back to the pool may be reused for a different workspace.
    """
    from sqlalchemy import text

    await conn.execute(  # type: ignore[union-attr]
        text("SELECT set_config('loop.workspace_id', :ws, true)"),
        {"ws": str(workspace_id)},
    )


def _row_to_agent(row: object) -> AgentRecord:
    return AgentRecord(
        id=row.id,  # type: ignore[attr-defined]
        workspace_id=row.workspace_id,  # type: ignore[attr-defined]
        name=row.name,  # type: ignore[attr-defined]
        slug=row.slug,  # type: ignore[attr-defined]
        description=row.description,  # type: ignore[attr-defined]
        created_at=row.created_at,  # type: ignore[attr-defined]
        archived_at=row.archived_at,  # type: ignore[attr-defined]
    )
