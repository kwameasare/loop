"""Integration tests for :class:`PostgresWorkspaceService` [P0.2].

Behavioural parity with :class:`WorkspaceService` is the core
contract; every test in this module also runs (or has a hermetic
twin) against the in-memory implementation in
``test_control_plane.py``. If a test passes against in-memory but
fails here, that is a divergence bug in ``PostgresWorkspaceService``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from loop_control_plane.regions import (
    Region,
    RegionRegistry,
)
from loop_control_plane.workspaces import (
    PostgresWorkspaceService,
    Role,
    WorkspaceError,
)
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

pytestmark = pytest.mark.integration


def _async_url(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def _two_region_registry() -> RegionRegistry:
    """Tiny region registry used by the integration tests so we don't
    have to depend on the ``infra/terraform/regions.yaml`` resolution
    path inside the testcontainer."""
    return RegionRegistry(
        default_region="na-east",
        regions={
            "na-east": Region(
                slug="na-east",
                display_name="NA East",
                residency="us",
                data_plane_url="https://dp-na-east.loop.local",
                concrete={"aws": "us-east-1"},
                primary=True,
            ),
            "eu-west": Region(
                slug="eu-west",
                display_name="EU West",
                residency="eu",
                data_plane_url="https://dp-eu-west.loop.local",
                concrete={"aws": "eu-west-1"},
            ),
        },
    )


def _reset_workspace_tables(engine: Engine) -> None:
    """Wipe workspaces + workspace_members between tests.

    Plain ``DELETE FROM workspaces`` fails because of a schema bug
    introduced by ``cp_0005_audit_log``: ``audit_log`` declares both
    ``ON DELETE CASCADE`` against ``workspaces`` AND a
    ``RULE no_delete_audit_log AS ON DELETE TO audit_log DO INSTEAD
    NOTHING``. The cascading delete is rewritten by the rule and
    Postgres errors out with "unexpected result" — even when
    ``audit_log`` is empty.

    TRUNCATE bypasses rules, but the unprivileged ``loop_app`` role
    can't TRUNCATE. We connect as the testcontainer's superuser
    purely for the teardown so each test sees an empty world.

    The schema bug itself (incompatible cascade + rule) is a
    pre-existing P1 to fix in a follow-up migration that picks one
    or the other.
    """
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
async def workspace_service(
    migrated_postgres_engine: Engine,
) -> AsyncIterator[PostgresWorkspaceService]:
    _reset_workspace_tables(migrated_postgres_engine)
    async_engine: AsyncEngine = create_async_engine(_async_url(migrated_postgres_engine))
    try:
        yield PostgresWorkspaceService(async_engine, regions=_two_region_registry())
    finally:
        await async_engine.dispose()


# --------------------------------------------------------------- create + get


@pytest.mark.asyncio
async def test_create_round_trips_through_get(
    workspace_service: PostgresWorkspaceService,
) -> None:
    ws = await workspace_service.create(
        name="Acme", slug="acme", owner_sub="auth0|alice"
    )
    found = await workspace_service.get(ws.id)
    assert found == ws
    assert found.created_by == "auth0|alice"


@pytest.mark.asyncio
async def test_create_makes_owner_member(
    workspace_service: PostgresWorkspaceService,
) -> None:
    ws = await workspace_service.create(
        name="Acme", slug="acme", owner_sub="auth0|alice"
    )
    role = await workspace_service.role_of(
        workspace_id=ws.id, user_sub="auth0|alice"
    )
    assert role is Role.OWNER


@pytest.mark.asyncio
async def test_duplicate_slug_rejected(
    workspace_service: PostgresWorkspaceService,
) -> None:
    await workspace_service.create(name="A", slug="a", owner_sub="u1")
    with pytest.raises(WorkspaceError, match="slug already taken"):
        await workspace_service.create(name="A2", slug="a", owner_sub="u2")


@pytest.mark.asyncio
async def test_create_rejects_unknown_region(
    workspace_service: PostgresWorkspaceService,
) -> None:
    with pytest.raises(WorkspaceError, match="unknown region"):
        await workspace_service.create(
            name="A", slug="a", owner_sub="u1", region="south-pole"
        )


@pytest.mark.asyncio
async def test_create_uses_default_region_when_unspecified(
    workspace_service: PostgresWorkspaceService,
) -> None:
    ws = await workspace_service.create(name="A", slug="a", owner_sub="u1")
    assert ws.region == "na-east"


@pytest.mark.asyncio
async def test_get_unknown_workspace_raises(
    workspace_service: PostgresWorkspaceService,
) -> None:
    from uuid import uuid4

    with pytest.raises(WorkspaceError, match="unknown workspace"):
        await workspace_service.get(uuid4())


# ------------------------------------------------------------ list_for_user


@pytest.mark.asyncio
async def test_list_for_user_returns_only_their_workspaces(
    workspace_service: PostgresWorkspaceService,
) -> None:
    a = await workspace_service.create(name="A", slug="a", owner_sub="alice")
    b = await workspace_service.create(name="B", slug="b", owner_sub="bob")
    await workspace_service.create(name="C", slug="c", owner_sub="bob")
    alice_ids = {w.id for w in await workspace_service.list_for_user("alice")}
    bob_ids = {w.id for w in await workspace_service.list_for_user("bob")}
    assert alice_ids == {a.id}
    assert b.id in bob_ids
    assert len(bob_ids) == 2


@pytest.mark.asyncio
async def test_list_for_user_includes_workspaces_joined_as_member(
    workspace_service: PostgresWorkspaceService,
) -> None:
    ws = await workspace_service.create(name="A", slug="a", owner_sub="alice")
    await workspace_service.add_member(
        workspace_id=ws.id, user_sub="bob", role=Role.MEMBER
    )
    bob_ids = {w.id for w in await workspace_service.list_for_user("bob")}
    assert ws.id in bob_ids


# ---------------------------------------------------------------- members


@pytest.mark.asyncio
async def test_add_member_then_role_of(
    workspace_service: PostgresWorkspaceService,
) -> None:
    ws = await workspace_service.create(name="A", slug="a", owner_sub="alice")
    await workspace_service.add_member(
        workspace_id=ws.id, user_sub="bob", role=Role.ADMIN
    )
    assert (
        await workspace_service.role_of(workspace_id=ws.id, user_sub="bob")
        is Role.ADMIN
    )


@pytest.mark.asyncio
async def test_add_member_overwrites_existing_role(
    workspace_service: PostgresWorkspaceService,
) -> None:
    ws = await workspace_service.create(name="A", slug="a", owner_sub="alice")
    await workspace_service.add_member(
        workspace_id=ws.id, user_sub="bob", role=Role.MEMBER
    )
    await workspace_service.add_member(
        workspace_id=ws.id, user_sub="bob", role=Role.ADMIN
    )
    assert (
        await workspace_service.role_of(workspace_id=ws.id, user_sub="bob")
        is Role.ADMIN
    )


@pytest.mark.asyncio
async def test_role_of_returns_none_for_non_member(
    workspace_service: PostgresWorkspaceService,
) -> None:
    ws = await workspace_service.create(name="A", slug="a", owner_sub="alice")
    role = await workspace_service.role_of(
        workspace_id=ws.id, user_sub="not-a-member"
    )
    assert role is None


@pytest.mark.asyncio
async def test_list_members_orders_by_creation(
    workspace_service: PostgresWorkspaceService,
) -> None:
    ws = await workspace_service.create(name="A", slug="a", owner_sub="alice")
    await workspace_service.add_member(
        workspace_id=ws.id, user_sub="bob", role=Role.MEMBER
    )
    await workspace_service.add_member(
        workspace_id=ws.id, user_sub="carol", role=Role.VIEWER
    )
    members = await workspace_service.list_members(ws.id)
    assert [m.user_sub for m in members] == ["alice", "bob", "carol"]


@pytest.mark.asyncio
async def test_list_members_unknown_workspace_raises(
    workspace_service: PostgresWorkspaceService,
) -> None:
    from uuid import uuid4

    with pytest.raises(WorkspaceError, match="unknown workspace"):
        await workspace_service.list_members(uuid4())


# --------------------------------------------------------- remove_member


@pytest.mark.asyncio
async def test_remove_member_drops_target(
    workspace_service: PostgresWorkspaceService,
) -> None:
    ws = await workspace_service.create(name="A", slug="a", owner_sub="alice")
    await workspace_service.add_member(
        workspace_id=ws.id, user_sub="bob", role=Role.MEMBER
    )
    await workspace_service.remove_member(
        workspace_id=ws.id, user_sub="bob", actor_sub="alice"
    )
    assert (
        await workspace_service.role_of(workspace_id=ws.id, user_sub="bob")
        is None
    )


@pytest.mark.asyncio
async def test_remove_member_refuses_last_owner(
    workspace_service: PostgresWorkspaceService,
) -> None:
    ws = await workspace_service.create(name="A", slug="a", owner_sub="alice")
    with pytest.raises(WorkspaceError, match="last owner"):
        await workspace_service.remove_member(
            workspace_id=ws.id, user_sub="alice", actor_sub="alice"
        )


@pytest.mark.asyncio
async def test_remove_member_allows_removing_owner_when_other_owner_exists(
    workspace_service: PostgresWorkspaceService,
) -> None:
    ws = await workspace_service.create(name="A", slug="a", owner_sub="alice")
    await workspace_service.add_member(
        workspace_id=ws.id, user_sub="bob", role=Role.OWNER
    )
    await workspace_service.remove_member(
        workspace_id=ws.id, user_sub="alice", actor_sub="bob"
    )
    assert (
        await workspace_service.role_of(workspace_id=ws.id, user_sub="alice")
        is None
    )


@pytest.mark.asyncio
async def test_remove_member_unknown_actor_rejected(
    workspace_service: PostgresWorkspaceService,
) -> None:
    ws = await workspace_service.create(name="A", slug="a", owner_sub="alice")
    with pytest.raises(WorkspaceError, match="not a member"):
        await workspace_service.remove_member(
            workspace_id=ws.id, user_sub="alice", actor_sub="eve"
        )


# ---------------------------------------------------------- update_role


@pytest.mark.asyncio
async def test_update_role_demotes_member(
    workspace_service: PostgresWorkspaceService,
) -> None:
    ws = await workspace_service.create(name="A", slug="a", owner_sub="alice")
    await workspace_service.add_member(
        workspace_id=ws.id, user_sub="bob", role=Role.ADMIN
    )
    await workspace_service.update_role(
        workspace_id=ws.id,
        user_sub="bob",
        role=Role.VIEWER,
        actor_sub="alice",
    )
    assert (
        await workspace_service.role_of(workspace_id=ws.id, user_sub="bob")
        is Role.VIEWER
    )


@pytest.mark.asyncio
async def test_update_role_refuses_to_demote_last_owner(
    workspace_service: PostgresWorkspaceService,
) -> None:
    ws = await workspace_service.create(name="A", slug="a", owner_sub="alice")
    with pytest.raises(WorkspaceError, match="last owner"):
        await workspace_service.update_role(
            workspace_id=ws.id,
            user_sub="alice",
            role=Role.ADMIN,
            actor_sub="alice",
        )


# ----------------------------------------------------------- update / delete


@pytest.mark.asyncio
async def test_update_changes_name(
    workspace_service: PostgresWorkspaceService,
) -> None:
    ws = await workspace_service.create(name="Old", slug="a", owner_sub="alice")
    updated = await workspace_service.update(
        workspace_id=ws.id, actor_sub="alice", name="New"
    )
    assert updated.name == "New"
    assert updated.id == ws.id
    assert (await workspace_service.get(ws.id)).name == "New"


@pytest.mark.asyncio
async def test_update_rejects_region_change(
    workspace_service: PostgresWorkspaceService,
) -> None:
    ws = await workspace_service.create(name="A", slug="a", owner_sub="alice")
    with pytest.raises(WorkspaceError, match="immutable"):
        await workspace_service.update(
            workspace_id=ws.id, actor_sub="alice", region="eu-west"
        )


@pytest.mark.asyncio
async def test_update_no_op_returns_current_snapshot(
    workspace_service: PostgresWorkspaceService,
) -> None:
    ws = await workspace_service.create(name="A", slug="a", owner_sub="alice")
    same = await workspace_service.update(workspace_id=ws.id, actor_sub="alice")
    assert same == ws


@pytest.mark.asyncio
async def test_update_rejects_non_member_actor(
    workspace_service: PostgresWorkspaceService,
) -> None:
    ws = await workspace_service.create(name="A", slug="a", owner_sub="alice")
    with pytest.raises(WorkspaceError, match="not a member"):
        await workspace_service.update(
            workspace_id=ws.id, actor_sub="eve", name="hax"
        )


@pytest.mark.asyncio
async def test_delete_only_owner_succeeds(
    workspace_service: PostgresWorkspaceService,
) -> None:
    ws = await workspace_service.create(name="A", slug="a", owner_sub="alice")
    await workspace_service.add_member(
        workspace_id=ws.id, user_sub="bob", role=Role.MEMBER
    )
    with pytest.raises(WorkspaceError, match="only the owner"):
        await workspace_service.delete(workspace_id=ws.id, actor_sub="bob")
    await workspace_service.delete(workspace_id=ws.id, actor_sub="alice")
    with pytest.raises(WorkspaceError, match="unknown workspace"):
        await workspace_service.get(ws.id)


@pytest.mark.asyncio
async def test_delete_cascades_membership(
    workspace_service: PostgresWorkspaceService,
) -> None:
    """workspace_members → workspaces FK is ON DELETE CASCADE; deleting
    the workspace must clear every member row so a re-create with the
    same slug does not inherit stale roles."""
    ws = await workspace_service.create(name="A", slug="a", owner_sub="alice")
    await workspace_service.add_member(
        workspace_id=ws.id, user_sub="bob", role=Role.MEMBER
    )
    await workspace_service.delete(workspace_id=ws.id, actor_sub="alice")
    new = await workspace_service.create(name="A2", slug="a", owner_sub="alice")
    assert (
        await workspace_service.role_of(workspace_id=new.id, user_sub="bob")
        is None
    )


# ----------------------------------------------------------- region helper


def test_require_same_region_passes_for_match(
    workspace_service: PostgresWorkspaceService,
) -> None:
    workspace_service.require_same_region(
        workspace_region="na-east", request_region="na-east"
    )


def test_require_same_region_raises_on_mismatch(
    workspace_service: PostgresWorkspaceService,
) -> None:
    from loop_control_plane.regions import RegionError

    with pytest.raises(RegionError, match="cross-region"):
        workspace_service.require_same_region(
            workspace_region="na-east", request_region="eu-west"
        )
