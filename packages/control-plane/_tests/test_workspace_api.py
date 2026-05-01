"""Tests for the workspace HTTP-shaped facade (S107-S110, S112)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from loop_control_plane.authorize import (
    AuthorisationError,
    authorize_workspace_access,
    role_satisfies,
)
from loop_control_plane.workspace_api import WorkspaceAPI
from loop_control_plane.workspaces import (
    Role,
    WorkspaceError,
    WorkspaceService,
)


@pytest.fixture
def svc() -> WorkspaceService:
    return WorkspaceService()


@pytest.fixture
def api(svc: WorkspaceService) -> WorkspaceAPI:
    return WorkspaceAPI(workspaces=svc)


# --------------------------------------------------------------------------- #
# S107 -- authorize_workspace_access                                          #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_role_satisfies_lattice() -> None:
    assert role_satisfies(Role.OWNER, Role.MEMBER)
    assert role_satisfies(Role.ADMIN, Role.MEMBER)
    assert role_satisfies(Role.MEMBER, Role.MEMBER)
    assert not role_satisfies(Role.VIEWER, Role.MEMBER)
    assert not role_satisfies(Role.MEMBER, Role.ADMIN)


@pytest.mark.asyncio
async def test_authorize_rejects_non_member(api: WorkspaceAPI, svc: WorkspaceService) -> None:
    body = await api.create(caller_sub="owner", body={"name": "Acme", "slug": "acme"})
    ws_id = UUID(body["id"])
    with pytest.raises(AuthorisationError):
        await authorize_workspace_access(workspaces=svc, workspace_id=ws_id, user_sub="stranger")


@pytest.mark.asyncio
async def test_authorize_unknown_workspace_raises_workspace_error(
    svc: WorkspaceService,
) -> None:
    with pytest.raises(WorkspaceError):
        await authorize_workspace_access(workspaces=svc, workspace_id=uuid4(), user_sub="anyone")


@pytest.mark.asyncio
async def test_authorize_role_hierarchy_allows_higher_role(
    api: WorkspaceAPI, svc: WorkspaceService
) -> None:
    body = await api.create(caller_sub="owner", body={"name": "Acme", "slug": "acme"})
    ws_id = UUID(body["id"])
    _, m = await authorize_workspace_access(
        workspaces=svc,
        workspace_id=ws_id,
        user_sub="owner",
        required_role=Role.MEMBER,
    )
    assert m.role is Role.OWNER


# --------------------------------------------------------------------------- #
# S108 -- create + S109 list                                                  #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_create_returns_serialised_workspace(api: WorkspaceAPI) -> None:
    body = await api.create(caller_sub="u-1", body={"name": "Acme", "slug": "acme"})
    assert body["name"] == "Acme"
    assert body["slug"] == "acme"
    assert body["region"] == "na-east"
    assert UUID(body["id"])  # raises if not a uuid
    assert body["created_by"] == "u-1"


@pytest.mark.asyncio
async def test_create_validates_inputs(api: WorkspaceAPI) -> None:
    with pytest.raises(WorkspaceError):
        await api.create(caller_sub="u-1", body={"slug": "acme"})
    with pytest.raises(WorkspaceError):
        await api.create(caller_sub="u-1", body={"name": "", "slug": "acme"})


@pytest.mark.asyncio
async def test_list_for_caller_paginates(api: WorkspaceAPI) -> None:
    for i in range(5):
        await api.create(caller_sub="u-1", body={"name": f"w{i}", "slug": f"w{i}"})
    page = await api.list_for_caller(caller_sub="u-1", page=1, page_size=2)
    assert len(page["items"]) == 2
    assert page["total"] == 5
    page2 = await api.list_for_caller(caller_sub="u-1", page=3, page_size=2)
    assert len(page2["items"]) == 1


@pytest.mark.asyncio
async def test_list_rejects_bad_pagination(api: WorkspaceAPI) -> None:
    with pytest.raises(WorkspaceError):
        await api.list_for_caller(caller_sub="u-1", page=0)
    with pytest.raises(WorkspaceError):
        await api.list_for_caller(caller_sub="u-1", page_size=0)
    with pytest.raises(WorkspaceError):
        await api.list_for_caller(caller_sub="u-1", page_size=1000)


# --------------------------------------------------------------------------- #
# S110 -- get + patch                                                         #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_get_requires_membership(api: WorkspaceAPI) -> None:
    body = await api.create(caller_sub="owner", body={"name": "Acme", "slug": "acme"})
    ws_id = UUID(body["id"])
    fetched = await api.get(caller_sub="owner", workspace_id=ws_id)
    assert fetched["id"] == body["id"]
    with pytest.raises(AuthorisationError):
        await api.get(caller_sub="stranger", workspace_id=ws_id)


@pytest.mark.asyncio
async def test_patch_owner_only_changes_name(api: WorkspaceAPI, svc: WorkspaceService) -> None:
    body = await api.create(caller_sub="owner", body={"name": "Old", "slug": "old"})
    ws_id = UUID(body["id"])
    await svc.add_member(workspace_id=ws_id, user_sub="member", role=Role.MEMBER)

    updated = await api.patch(caller_sub="owner", workspace_id=ws_id, body={"name": "New"})
    assert updated["name"] == "New"

    with pytest.raises(AuthorisationError):
        await api.patch(caller_sub="member", workspace_id=ws_id, body={"name": "Hacked"})


# --------------------------------------------------------------------------- #
# S112 -- members                                                             #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_member_lifecycle(api: WorkspaceAPI) -> None:
    body = await api.create(caller_sub="owner", body={"name": "Acme", "slug": "acme"})
    ws_id = UUID(body["id"])

    added = await api.add_member(
        caller_sub="owner",
        workspace_id=ws_id,
        body={"user_sub": "alice", "role": "admin"},
    )
    assert added["role"] == "admin"

    members = await api.list_members(caller_sub="owner", workspace_id=ws_id)
    assert {m["user_sub"] for m in members["items"]} == {"owner", "alice"}

    promoted = await api.update_member_role(
        caller_sub="owner",
        workspace_id=ws_id,
        user_sub="alice",
        body={"role": "owner"},
    )
    assert promoted["role"] == "owner"

    removed = await api.remove_member(caller_sub="owner", workspace_id=ws_id, user_sub="alice")
    assert removed["removed"] is True


@pytest.mark.asyncio
async def test_cannot_remove_last_owner(api: WorkspaceAPI) -> None:
    body = await api.create(caller_sub="owner", body={"name": "Acme", "slug": "acme"})
    ws_id = UUID(body["id"])
    with pytest.raises(WorkspaceError):
        await api.remove_member(caller_sub="owner", workspace_id=ws_id, user_sub="owner")


@pytest.mark.asyncio
async def test_cannot_demote_last_owner(api: WorkspaceAPI) -> None:
    body = await api.create(caller_sub="owner", body={"name": "Acme", "slug": "acme"})
    ws_id = UUID(body["id"])
    with pytest.raises(WorkspaceError):
        await api.update_member_role(
            caller_sub="owner",
            workspace_id=ws_id,
            user_sub="owner",
            body={"role": "admin"},
        )


@pytest.mark.asyncio
async def test_member_endpoints_require_owner(api: WorkspaceAPI, svc: WorkspaceService) -> None:
    body = await api.create(caller_sub="owner", body={"name": "Acme", "slug": "acme"})
    ws_id = UUID(body["id"])
    await svc.add_member(workspace_id=ws_id, user_sub="member", role=Role.MEMBER)

    # listing only requires plain membership
    listed = await api.list_members(caller_sub="member", workspace_id=ws_id)
    assert len(listed["items"]) == 2

    # but mutation does not
    with pytest.raises(AuthorisationError):
        await api.add_member(
            caller_sub="member",
            workspace_id=ws_id,
            body={"user_sub": "x", "role": "member"},
        )
    with pytest.raises(AuthorisationError):
        await api.remove_member(caller_sub="member", workspace_id=ws_id, user_sub="member")
    with pytest.raises(AuthorisationError):
        await api.update_member_role(
            caller_sub="member",
            workspace_id=ws_id,
            user_sub="member",
            body={"role": "admin"},
        )
