"""Tests for SCIM 2.0 provisioning service — S611.

Coverage:
- User CRUD: create, get, list (with filter), replace (PUT), patch (PATCH), delete
- Group CRUD: create, get, list, replace, patch (add/remove/replace members), delete
- Consistency: group membership mirrored in user.groups
- Error cases: duplicate userName, not-found, missing required fields
- ServiceProviderConfig document
"""

from __future__ import annotations

import pytest
from loop_control_plane.scim import (
    SCIMError,
    SCIMGroup,
    SCIMService,
    SCIMUser,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def svc() -> SCIMService:
    return SCIMService()


def _user_payload(
    username: str = "alice@example.com", *, active: bool = True
) -> dict:
    return {
        "userName": username,
        "displayName": "Alice Smith",
        "name": {"givenName": "Alice", "familyName": "Smith"},
        "emails": [{"value": username, "type": "work", "primary": True}],
        "active": active,
    }


def _group_payload(name: str = "Loop-Admins") -> dict:
    return {"displayName": name}


# ---------------------------------------------------------------------------
# User tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_user_returns_scim_user(svc: SCIMService) -> None:
    user = await svc.create_user(_user_payload())
    assert isinstance(user, SCIMUser)
    assert user.userName == "alice@example.com"
    assert user.active is True
    assert user.id  # UUID assigned


@pytest.mark.asyncio
async def test_create_user_duplicate_username_raises(svc: SCIMService) -> None:
    await svc.create_user(_user_payload())
    with pytest.raises(SCIMError, match="already exists"):
        await svc.create_user(_user_payload())


@pytest.mark.asyncio
async def test_create_user_missing_username_raises(svc: SCIMService) -> None:
    with pytest.raises(SCIMError, match="userName is required"):
        await svc.create_user({"displayName": "No Name"})


@pytest.mark.asyncio
async def test_get_user(svc: SCIMService) -> None:
    created = await svc.create_user(_user_payload())
    fetched = await svc.get_user(created.id)
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_get_user_not_found(svc: SCIMService) -> None:
    with pytest.raises(SCIMError) as exc_info:
        await svc.get_user("nonexistent-id")
    assert exc_info.value.status == 404


@pytest.mark.asyncio
async def test_list_users_no_filter(svc: SCIMService) -> None:
    await svc.create_user(_user_payload("alice@example.com"))
    await svc.create_user(_user_payload("bob@example.com"))
    users, total = await svc.list_users()
    assert total == 2
    assert len(users) == 2


@pytest.mark.asyncio
async def test_list_users_with_eq_filter(svc: SCIMService) -> None:
    await svc.create_user(_user_payload("alice@example.com"))
    await svc.create_user(_user_payload("bob@example.com"))
    users, total = await svc.list_users(
        filter_str='userName eq "alice@example.com"'
    )
    assert total == 1
    assert users[0].userName == "alice@example.com"


@pytest.mark.asyncio
async def test_replace_user_put(svc: SCIMService) -> None:
    user = await svc.create_user(_user_payload())
    updated = await svc.replace_user(
        user.id,
        {
            "userName": "alice@example.com",
            "displayName": "Alice Updated",
            "active": False,
        },
    )
    assert updated.displayName == "Alice Updated"
    assert updated.active is False


@pytest.mark.asyncio
async def test_patch_user_deactivate(svc: SCIMService) -> None:
    user = await svc.create_user(_user_payload())
    patched = await svc.patch_user(
        user.id,
        [{"op": "replace", "path": "active", "value": False}],
    )
    assert patched.active is False


@pytest.mark.asyncio
async def test_delete_user(svc: SCIMService) -> None:
    user = await svc.create_user(_user_payload())
    await svc.delete_user(user.id)
    with pytest.raises(SCIMError) as exc_info:
        await svc.get_user(user.id)
    assert exc_info.value.status == 404


@pytest.mark.asyncio
async def test_delete_user_removes_from_groups(svc: SCIMService) -> None:
    user = await svc.create_user(_user_payload())
    group = await svc.create_group(
        {"displayName": "Loop-Admins", "members": [{"value": user.id}]}
    )
    await svc.delete_user(user.id)
    updated_group = await svc.get_group(group.id)
    assert all(m.value != user.id for m in updated_group.members)


# ---------------------------------------------------------------------------
# Group tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_group_returns_scim_group(svc: SCIMService) -> None:
    group = await svc.create_group(_group_payload())
    assert isinstance(group, SCIMGroup)
    assert group.displayName == "Loop-Admins"
    assert group.id


@pytest.mark.asyncio
async def test_create_group_missing_display_name_raises(
    svc: SCIMService,
) -> None:
    with pytest.raises(SCIMError, match="displayName is required"):
        await svc.create_group({})


@pytest.mark.asyncio
async def test_get_group_not_found(svc: SCIMService) -> None:
    with pytest.raises(SCIMError) as exc_info:
        await svc.get_group("nope")
    assert exc_info.value.status == 404


@pytest.mark.asyncio
async def test_list_groups(svc: SCIMService) -> None:
    await svc.create_group(_group_payload("Admins"))
    await svc.create_group(_group_payload("Editors"))
    _groups, total = await svc.list_groups()
    assert total == 2


@pytest.mark.asyncio
async def test_patch_group_add_member(svc: SCIMService) -> None:
    user = await svc.create_user(_user_payload())
    group = await svc.create_group(_group_payload())
    patched = await svc.patch_group(
        group.id,
        [{"op": "add", "path": "members", "value": [{"value": user.id}]}],
    )
    assert any(m.value == user.id for m in patched.members)


@pytest.mark.asyncio
async def test_patch_group_remove_member(svc: SCIMService) -> None:
    user = await svc.create_user(_user_payload())
    group = await svc.create_group(
        {"displayName": "Admins", "members": [{"value": user.id}]}
    )
    patched = await svc.patch_group(
        group.id,
        [{"op": "remove", "path": "members", "value": [{"value": user.id}]}],
    )
    assert not any(m.value == user.id for m in patched.members)


@pytest.mark.asyncio
async def test_delete_group(svc: SCIMService) -> None:
    group = await svc.create_group(_group_payload())
    await svc.delete_group(group.id)
    with pytest.raises(SCIMError) as exc_info:
        await svc.get_group(group.id)
    assert exc_info.value.status == 404


# ---------------------------------------------------------------------------
# Consistency: user.groups ↔ group.members
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_group_membership_reflected_in_user(svc: SCIMService) -> None:
    user = await svc.create_user(_user_payload())
    group = await svc.create_group(
        {"displayName": "Admins", "members": [{"value": user.id}]}
    )
    updated_user = await svc.get_user(user.id)
    assert group.id in updated_user.groups


@pytest.mark.asyncio
async def test_remove_user_from_group_clears_user_groups(
    svc: SCIMService,
) -> None:
    user = await svc.create_user(_user_payload())
    group = await svc.create_group(
        {"displayName": "Admins", "members": [{"value": user.id}]}
    )
    # Remove member via PATCH
    await svc.patch_group(
        group.id,
        [{"op": "remove", "path": "members", "value": [{"value": user.id}]}],
    )
    updated_user = await svc.get_user(user.id)
    assert group.id not in updated_user.groups


@pytest.mark.asyncio
async def test_delete_group_clears_user_groups(svc: SCIMService) -> None:
    user = await svc.create_user(_user_payload())
    group = await svc.create_group(
        {"displayName": "Admins", "members": [{"value": user.id}]}
    )
    await svc.delete_group(group.id)
    updated_user = await svc.get_user(user.id)
    assert group.id not in updated_user.groups


# ---------------------------------------------------------------------------
# to_scim serialisation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_to_scim_structure(svc: SCIMService) -> None:
    user = await svc.create_user(_user_payload())
    doc = user.to_scim()
    assert "urn:ietf:params:scim:schemas:core:2.0:User" in doc["schemas"]
    assert doc["id"] == user.id
    assert doc["userName"] == user.userName
    assert "meta" in doc


@pytest.mark.asyncio
async def test_group_to_scim_structure(svc: SCIMService) -> None:
    group = await svc.create_group(_group_payload())
    doc = group.to_scim()
    assert "urn:ietf:params:scim:schemas:core:2.0:Group" in doc["schemas"]
    assert doc["displayName"] == group.displayName


# ---------------------------------------------------------------------------
# ServiceProviderConfig
# ---------------------------------------------------------------------------


def test_service_provider_config_document() -> None:
    cfg = SCIMService.service_provider_config()
    assert cfg["patch"]["supported"] is True
    assert cfg["filter"]["supported"] is True
    assert "authenticationSchemes" in cfg


# ---------------------------------------------------------------------------
# SCIMError helper
# ---------------------------------------------------------------------------


def test_scim_error_to_dict() -> None:
    err = SCIMError("not found", 404)
    d = err.to_dict()
    assert d["status"] == "404"
    assert "urn:ietf:params:scim:api:messages:2.0:Error" in d["schemas"]
