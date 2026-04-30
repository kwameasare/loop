"""Tests for the API-key HTTP-shaped facade (S113-S115)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from loop_control_plane.api_keys import ApiKeyError, ApiKeyService
from loop_control_plane.api_keys_api import ApiKeyAPI
from loop_control_plane.authorize import AuthorisationError
from loop_control_plane.workspaces import Role, WorkspaceService


@pytest.fixture
async def fixture_workspace() -> tuple[ApiKeyAPI, WorkspaceService, UUID]:
    ws_svc = WorkspaceService()
    ak_svc = ApiKeyService()
    ws = await ws_svc.create(name="Acme", slug="acme", owner_sub="owner")
    await ws_svc.add_member(workspace_id=ws.id, user_sub="admin", role=Role.ADMIN)
    await ws_svc.add_member(workspace_id=ws.id, user_sub="member", role=Role.MEMBER)
    api = ApiKeyAPI(api_keys=ak_svc, workspaces=ws_svc)
    return api, ws_svc, ws.id


@pytest.mark.asyncio
async def test_create_returns_plaintext_once(
    fixture_workspace: tuple[ApiKeyAPI, WorkspaceService, UUID],
) -> None:
    api, _, ws_id = fixture_workspace
    body = await api.create(
        caller_sub="owner",
        workspace_id=ws_id,
        body={"name": "ci-key"},
    )
    assert body["name"] == "ci-key"
    assert body["plaintext"].startswith("loop_sk_")
    assert body["prefix"]
    # listed records must NOT carry the plaintext
    listed = await api.list_for_workspace(caller_sub="owner", workspace_id=ws_id)
    assert listed["items"][0].get("plaintext") is None


@pytest.mark.asyncio
async def test_create_rejects_non_admin(
    fixture_workspace: tuple[ApiKeyAPI, WorkspaceService, UUID],
) -> None:
    api, _, ws_id = fixture_workspace
    with pytest.raises(AuthorisationError):
        await api.create(
            caller_sub="member", workspace_id=ws_id, body={"name": "x"}
        )


@pytest.mark.asyncio
async def test_create_validates_name(
    fixture_workspace: tuple[ApiKeyAPI, WorkspaceService, UUID],
) -> None:
    api, _, ws_id = fixture_workspace
    with pytest.raises(ApiKeyError):
        await api.create(caller_sub="owner", workspace_id=ws_id, body={})


@pytest.mark.asyncio
async def test_list_requires_only_membership(
    fixture_workspace: tuple[ApiKeyAPI, WorkspaceService, UUID],
) -> None:
    api, _, ws_id = fixture_workspace
    await api.create(caller_sub="owner", workspace_id=ws_id, body={"name": "k1"})
    listed = await api.list_for_workspace(caller_sub="member", workspace_id=ws_id)
    assert len(listed["items"]) == 1
    with pytest.raises(AuthorisationError):
        await api.list_for_workspace(caller_sub="stranger", workspace_id=ws_id)


@pytest.mark.asyncio
async def test_revoke_marks_record_and_is_idempotent(
    fixture_workspace: tuple[ApiKeyAPI, WorkspaceService, UUID],
) -> None:
    api, _, ws_id = fixture_workspace
    issued = await api.create(
        caller_sub="owner", workspace_id=ws_id, body={"name": "k"}
    )
    key_id = UUID(issued["id"])
    revoked = await api.revoke(
        caller_sub="admin", workspace_id=ws_id, key_id=key_id
    )
    assert revoked["revoked_at"] is not None
    # second revoke should still succeed (service is idempotent)
    again = await api.revoke(caller_sub="admin", workspace_id=ws_id, key_id=key_id)
    assert again["revoked_at"] is not None


@pytest.mark.asyncio
async def test_revoke_rejects_member(
    fixture_workspace: tuple[ApiKeyAPI, WorkspaceService, UUID],
) -> None:
    api, _, ws_id = fixture_workspace
    issued = await api.create(
        caller_sub="owner", workspace_id=ws_id, body={"name": "k"}
    )
    with pytest.raises(AuthorisationError):
        await api.revoke(
            caller_sub="member",
            workspace_id=ws_id,
            key_id=UUID(issued["id"]),
        )


@pytest.mark.asyncio
async def test_revoke_unknown_key_in_workspace(
    fixture_workspace: tuple[ApiKeyAPI, WorkspaceService, UUID],
) -> None:
    api, _, ws_id = fixture_workspace
    with pytest.raises(ApiKeyError):
        await api.revoke(caller_sub="owner", workspace_id=ws_id, key_id=uuid4())
