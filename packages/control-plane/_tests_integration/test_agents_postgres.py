"""Integration tests for :class:`PostgresAgentRegistry` [P0.2]."""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from loop_control_plane._app_agents import (
    AgentCreate,
    PostgresAgentRegistry,
)
from loop_control_plane.workspaces import WorkspaceError
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

pytestmark = pytest.mark.integration


def _async_url(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def _seed_workspace(engine: Engine) -> UUID:
    """Insert a workspace row directly so agent FK is satisfied.

    Goes through the loop_app role rather than the superuser since
    PostgresWorkspaceService is the production caller. Returns the
    new UUID.
    """
    ws_id = uuid4()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO workspaces (
                    id, name, slug, region, tenant_kms_key_id,
                    created_at, created_by
                ) VALUES (
                    :id, 'fixture', :slug, 'na-east',
                    'vault://transit/workspace/fixture', now(), 'fixture-user'
                )
                """
            ),
            {"id": ws_id, "slug": f"fixture-{ws_id.hex[:8]}"},
        )
    return ws_id


def _reset_agent_tables(engine: Engine) -> None:
    """Wipe agents + workspaces between tests via the testcontainers
    superuser; same workaround as ``test_workspaces_postgres.py``."""
    from sqlalchemy import create_engine

    admin_url = engine.url.set(username="test", password="test")
    admin_engine = create_engine(admin_url)
    try:
        with admin_engine.begin() as conn:
            conn.execute(
                text("TRUNCATE TABLE workspaces RESTART IDENTITY CASCADE")
            )
    finally:
        admin_engine.dispose()


@pytest_asyncio.fixture
async def agent_registry_with_workspace(
    migrated_postgres_engine: Engine,
) -> AsyncIterator[tuple[PostgresAgentRegistry, UUID]]:
    _reset_agent_tables(migrated_postgres_engine)
    workspace_id = _seed_workspace(migrated_postgres_engine)
    async_engine: AsyncEngine = create_async_engine(_async_url(migrated_postgres_engine))
    try:
        yield PostgresAgentRegistry(async_engine), workspace_id
    finally:
        await async_engine.dispose()


@pytest.mark.asyncio
async def test_create_round_trips_through_get(
    agent_registry_with_workspace: tuple[PostgresAgentRegistry, object],
) -> None:
    registry, workspace_id = agent_registry_with_workspace
    created = await registry.create(
        workspace_id=workspace_id,
        body=AgentCreate(name="Support", slug="support", description="frontline"),
    )
    found = await registry.get(workspace_id=workspace_id, agent_id=created.id)
    assert found == created
    assert found.archived_at is None


@pytest.mark.asyncio
async def test_create_rejects_duplicate_slug_in_same_workspace(
    agent_registry_with_workspace: tuple[PostgresAgentRegistry, object],
) -> None:
    registry, workspace_id = agent_registry_with_workspace
    await registry.create(
        workspace_id=workspace_id, body=AgentCreate(name="A", slug="a")
    )
    with pytest.raises(WorkspaceError, match="agent slug already taken"):
        await registry.create(
            workspace_id=workspace_id, body=AgentCreate(name="A2", slug="a")
        )


@pytest.mark.asyncio
async def test_create_allows_same_slug_in_different_workspaces(
    migrated_postgres_engine: Engine,
    agent_registry_with_workspace: tuple[PostgresAgentRegistry, object],
) -> None:
    """The UNIQUE constraint is (workspace_id, slug); a slug taken in
    workspace A must remain available in workspace B."""
    registry, workspace_a = agent_registry_with_workspace
    workspace_b = _seed_workspace(migrated_postgres_engine)
    await registry.create(
        workspace_id=workspace_a, body=AgentCreate(name="A", slug="shared")
    )
    in_b = await registry.create(
        workspace_id=workspace_b, body=AgentCreate(name="B", slug="shared")
    )
    assert in_b.workspace_id == workspace_b


@pytest.mark.asyncio
async def test_list_for_workspace_excludes_archived(
    agent_registry_with_workspace: tuple[PostgresAgentRegistry, object],
) -> None:
    registry, workspace_id = agent_registry_with_workspace
    a = await registry.create(
        workspace_id=workspace_id, body=AgentCreate(name="A", slug="a")
    )
    await registry.create(
        workspace_id=workspace_id, body=AgentCreate(name="B", slug="b")
    )
    await registry.archive(workspace_id=workspace_id, agent_id=a.id)
    listed = await registry.list_for_workspace(workspace_id)
    assert {x.slug for x in listed} == {"b"}


@pytest.mark.asyncio
async def test_list_for_workspace_orders_by_created_at(
    agent_registry_with_workspace: tuple[PostgresAgentRegistry, object],
) -> None:
    registry, workspace_id = agent_registry_with_workspace
    first = await registry.create(
        workspace_id=workspace_id, body=AgentCreate(name="First", slug="first")
    )
    second = await registry.create(
        workspace_id=workspace_id, body=AgentCreate(name="Second", slug="second")
    )
    listed = await registry.list_for_workspace(workspace_id)
    assert [x.id for x in listed] == [first.id, second.id]


@pytest.mark.asyncio
async def test_get_unknown_agent_raises(
    agent_registry_with_workspace: tuple[PostgresAgentRegistry, object],
) -> None:
    registry, workspace_id = agent_registry_with_workspace
    with pytest.raises(WorkspaceError, match="unknown agent"):
        await registry.get(workspace_id=workspace_id, agent_id=uuid4())


@pytest.mark.asyncio
async def test_get_in_wrong_workspace_raises(
    migrated_postgres_engine: Engine,
    agent_registry_with_workspace: tuple[PostgresAgentRegistry, object],
) -> None:
    """A leaked agent UUID must not be readable from a different
    workspace context — the query filters on workspace_id."""
    registry, workspace_a = agent_registry_with_workspace
    a = await registry.create(
        workspace_id=workspace_a, body=AgentCreate(name="A", slug="a")
    )
    workspace_b = _seed_workspace(migrated_postgres_engine)
    with pytest.raises(WorkspaceError, match="unknown agent"):
        await registry.get(workspace_id=workspace_b, agent_id=a.id)


@pytest.mark.asyncio
async def test_get_archived_agent_raises(
    agent_registry_with_workspace: tuple[PostgresAgentRegistry, object],
) -> None:
    """Archived agents are not visible via get() — same as in-memory."""
    registry, workspace_id = agent_registry_with_workspace
    a = await registry.create(
        workspace_id=workspace_id, body=AgentCreate(name="A", slug="a")
    )
    await registry.archive(workspace_id=workspace_id, agent_id=a.id)
    with pytest.raises(WorkspaceError, match="unknown agent"):
        await registry.get(workspace_id=workspace_id, agent_id=a.id)


@pytest.mark.asyncio
async def test_archive_unknown_agent_raises(
    agent_registry_with_workspace: tuple[PostgresAgentRegistry, object],
) -> None:
    registry, workspace_id = agent_registry_with_workspace
    with pytest.raises(WorkspaceError, match="unknown agent"):
        await registry.archive(workspace_id=workspace_id, agent_id=uuid4())


@pytest.mark.asyncio
async def test_archive_already_archived_agent_raises(
    agent_registry_with_workspace: tuple[PostgresAgentRegistry, object],
) -> None:
    """Double-archiving must surface as ``unknown agent`` because the
    second call's WHERE clause excludes already-archived rows. Matches
    the in-memory contract."""
    registry, workspace_id = agent_registry_with_workspace
    a = await registry.create(
        workspace_id=workspace_id, body=AgentCreate(name="A", slug="a")
    )
    await registry.archive(workspace_id=workspace_id, agent_id=a.id)
    with pytest.raises(WorkspaceError, match="unknown agent"):
        await registry.archive(workspace_id=workspace_id, agent_id=a.id)


@pytest.mark.asyncio
async def test_create_in_unknown_workspace_raises(
    migrated_postgres_engine: Engine,
    agent_registry_with_workspace: tuple[PostgresAgentRegistry, object],
) -> None:
    """The agents.workspace_id FK rejects an agent for a non-existent
    workspace. The IntegrityError is translated to WorkspaceError
    (matches in-memory's "unknown workspace" semantics for this
    failure mode, even though the message is slug-themed). The same
    failure surface is what the route handler maps to 4xx."""
    registry, _ = agent_registry_with_workspace
    with pytest.raises(WorkspaceError):
        await registry.create(
            workspace_id=uuid4(), body=AgentCreate(name="A", slug="a")
        )
