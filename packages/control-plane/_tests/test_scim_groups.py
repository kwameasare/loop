"""SCIM 2.0 group lifecycle tests (S611).

Group CRUD with member add/remove via PatchOp — the path Okta and
Entra use to drive Loop's group→role mapping. RFC 7644 §3.5.2.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from loop_control_plane.scim import (
    ScimError,
    apply_patch_to_group,
    parse_group,
    parse_patch_op,
    parse_scim_filter,
    parse_user,
    service_provider_config,
)
from loop_control_plane.scim_store import InMemoryScimStore


TENANT = "tenant-acme"
NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


def _group(display: str = "Loop-Editors", members: list | None = None) -> dict[str, object]:
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "displayName": display,
        "members": members or [],
    }


def _seed_user(store: InMemoryScimStore, user_name: str) -> str:
    payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": user_name,
    }
    user = store.create_user(TENANT, parse_user(payload), NOW)
    return user.id


def test_create_group_assigns_id_and_meta() -> None:
    store = InMemoryScimStore()
    group = store.create_group(TENANT, parse_group(_group()), NOW)
    assert group.id.startswith("g-")
    assert group.meta is not None
    assert group.meta.resource_type == "Group"


def test_duplicate_displayname_returns_uniqueness_409() -> None:
    store = InMemoryScimStore()
    store.create_group(TENANT, parse_group(_group("Loop-Admins")), NOW)
    with pytest.raises(ScimError) as exc:
        store.create_group(TENANT, parse_group(_group("Loop-Admins")), NOW)
    assert exc.value.status == 409


def test_list_groups_filter_by_display_name() -> None:
    store = InMemoryScimStore()
    store.create_group(TENANT, parse_group(_group("Loop-Admins")), NOW)
    store.create_group(TENANT, parse_group(_group("Loop-Editors")), NOW)
    page, total = store.list_groups(
        TENANT, parse_scim_filter('displayName eq "Loop-Admins"'), 1, 50
    )
    assert total == 1
    assert page[0].display_name == "Loop-Admins"


def test_patch_group_add_members_idempotent() -> None:
    store = InMemoryScimStore()
    group = store.create_group(TENANT, parse_group(_group()), NOW)
    user_id = _seed_user(store, "alice@example.com")
    patch = parse_patch_op(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {
                    "op": "add",
                    "path": "members",
                    "value": [{"value": user_id, "display": "alice@example.com"}],
                }
            ],
        }
    )
    updated = apply_patch_to_group(group, patch, NOW)
    assert any(m["value"] == user_id for m in updated.members)
    # Second add must not duplicate.
    again = apply_patch_to_group(updated, patch, NOW)
    assert sum(1 for m in again.members if m["value"] == user_id) == 1


def test_patch_group_remove_member_via_filter_path() -> None:
    """Okta convention: ``path: 'members[value eq "<id>"]'``."""
    store = InMemoryScimStore()
    user_id = _seed_user(store, "bob@example.com")
    group = store.create_group(
        TENANT,
        parse_group(_group(members=[{"value": user_id}])),
        NOW,
    )
    patch = parse_patch_op(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "remove", "path": f'members[value eq "{user_id}"]'}],
        }
    )
    updated = apply_patch_to_group(group, patch, NOW)
    assert updated.members == []


def test_patch_group_replace_display_name() -> None:
    store = InMemoryScimStore()
    group = store.create_group(TENANT, parse_group(_group("Old-Name")), NOW)
    patch = parse_patch_op(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "replace", "path": "displayName", "value": "New-Name"}],
        }
    )
    updated = apply_patch_to_group(group, patch, NOW)
    assert updated.display_name == "New-Name"


def test_patch_group_remove_displayname_rejected() -> None:
    store = InMemoryScimStore()
    group = store.create_group(TENANT, parse_group(_group("X")), NOW)
    patch = parse_patch_op(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "remove", "path": "displayName"}],
        }
    )
    with pytest.raises(ScimError) as exc:
        apply_patch_to_group(group, patch, NOW)
    assert exc.value.scim_type == "mutability"


def test_delete_user_cascades_membership() -> None:
    """Deleting a user must drop them from every group's members
    list — otherwise stale references leak into role projection."""
    store = InMemoryScimStore()
    user_id = _seed_user(store, "carol@example.com")
    group = store.create_group(
        TENANT,
        parse_group(_group(members=[{"value": user_id}])),
        NOW,
    )
    store.delete_user(TENANT, user_id)
    refreshed = store.get_group(TENANT, group.id)
    assert refreshed is not None
    assert refreshed.members == []


def test_replace_group_preserves_created_timestamp() -> None:
    store = InMemoryScimStore()
    group = store.create_group(TENANT, parse_group(_group("A")), NOW)
    later = datetime(2026, 6, 1, tzinfo=UTC)
    replaced = store.replace_group(TENANT, group.id, parse_group(_group("B")), later)
    assert replaced.display_name == "B"
    assert replaced.meta is not None
    assert replaced.meta.created == NOW
    assert replaced.meta.last_modified == later


def test_service_provider_config_advertises_capabilities() -> None:
    cfg = service_provider_config()
    assert cfg["patch"]["supported"] is True
    assert cfg["filter"]["supported"] is True
    assert cfg["bulk"]["supported"] is False
    assert cfg["authenticationSchemes"][0]["type"] == "oauthbearertoken"
