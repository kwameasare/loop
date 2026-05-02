"""SCIM 2.0 user lifecycle tests (S611).

Covers RFC 7644 §3.3 (create), §3.4 (list/get/filter), §3.5.1 (PUT
replace), §3.5.2 (PatchOp), §3.6 (DELETE) for the User resource.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from loop_control_plane.scim import (
    ScimError,
    apply_patch_to_user,
    parse_patch_op,
    parse_scim_filter,
    parse_user,
)
from loop_control_plane.scim_store import InMemoryScimStore


TENANT = "tenant-acme"
NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


def _alice() -> dict[str, object]:
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "alice@example.com",
        "name": {"givenName": "Alice", "familyName": "Anderson"},
        "emails": [{"value": "alice@example.com", "primary": True}],
        "externalId": "okta-00u1abcd",
        "active": True,
    }


def test_create_user_assigns_id_and_meta() -> None:
    store = InMemoryScimStore()
    user = parse_user(_alice())
    created = store.create_user(TENANT, user, NOW)
    assert created.id.startswith("u-")
    assert created.meta is not None
    assert created.meta.created == NOW
    assert created.meta.version.startswith('W/"')


def test_create_user_emits_scim_resource() -> None:
    store = InMemoryScimStore()
    created = store.create_user(TENANT, parse_user(_alice()), NOW)
    body = created.to_resource()
    assert body["schemas"] == ["urn:ietf:params:scim:schemas:core:2.0:User"]
    assert body["userName"] == "alice@example.com"
    assert body["name"]["givenName"] == "Alice"
    assert body["meta"]["resourceType"] == "User"


def test_create_user_rejects_missing_username() -> None:
    bad = _alice()
    bad.pop("userName")
    with pytest.raises(ScimError) as exc:
        parse_user(bad)
    assert exc.value.status == 400
    assert exc.value.scim_type == "invalidValue"


def test_duplicate_username_returns_uniqueness_409() -> None:
    store = InMemoryScimStore()
    store.create_user(TENANT, parse_user(_alice()), NOW)
    with pytest.raises(ScimError) as exc:
        store.create_user(TENANT, parse_user(_alice()), NOW)
    assert exc.value.status == 409
    assert exc.value.scim_type == "uniqueness"


def test_list_users_filter_by_username() -> None:
    store = InMemoryScimStore()
    store.create_user(TENANT, parse_user(_alice()), NOW)
    bob = _alice() | {"userName": "bob@example.com", "externalId": "okta-bob"}
    store.create_user(TENANT, parse_user(bob), NOW)

    page, total = store.list_users(
        TENANT, parse_scim_filter('userName eq "alice@example.com"'), 1, 50
    )
    assert total == 1
    assert page[0].user_name == "alice@example.com"


def test_list_users_pagination() -> None:
    store = InMemoryScimStore()
    for i in range(5):
        u = _alice() | {"userName": f"u{i}@example.com", "externalId": f"x-{i}"}
        store.create_user(TENANT, parse_user(u), NOW)
    page, total = store.list_users(TENANT, None, start_index=2, count=2)
    assert total == 5
    assert len(page) == 2


def test_replace_user_preserves_created_timestamp() -> None:
    store = InMemoryScimStore()
    created = store.create_user(TENANT, parse_user(_alice()), NOW)
    later = datetime(2026, 5, 2, 12, 0, tzinfo=UTC)
    new_payload = _alice() | {"name": {"givenName": "Alicia", "familyName": "Anderson"}}
    replaced = store.replace_user(TENANT, created.id, parse_user(new_payload), later)
    assert replaced.given_name == "Alicia"
    assert replaced.meta is not None
    assert replaced.meta.created == NOW
    assert replaced.meta.last_modified == later


def test_patch_user_deactivate() -> None:
    store = InMemoryScimStore()
    created = store.create_user(TENANT, parse_user(_alice()), NOW)
    patch = parse_patch_op(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "replace", "path": "active", "value": False}],
        }
    )
    later = datetime(2026, 5, 3, tzinfo=UTC)
    updated = apply_patch_to_user(created, patch, later)
    store.update_user(TENANT, created.id, updated)
    assert store.get_user(TENANT, created.id).active is False


def test_patch_user_okta_envelope_no_path() -> None:
    """Okta sends ``{"op":"replace","value":{"active":false}}`` without
    ``path``; we must accept that envelope."""
    store = InMemoryScimStore()
    created = store.create_user(TENANT, parse_user(_alice()), NOW)
    patch = parse_patch_op(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "replace", "value": {"active": False}}],
        }
    )
    updated = apply_patch_to_user(created, patch, NOW)
    assert updated.active is False


def test_patch_user_invalid_path_errors() -> None:
    store = InMemoryScimStore()
    created = store.create_user(TENANT, parse_user(_alice()), NOW)
    patch = parse_patch_op(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "replace", "path": "password", "value": "hunter2"}],
        }
    )
    with pytest.raises(ScimError) as exc:
        apply_patch_to_user(created, patch, NOW)
    assert exc.value.scim_type == "invalidPath"


def test_delete_user_idempotency_404() -> None:
    store = InMemoryScimStore()
    created = store.create_user(TENANT, parse_user(_alice()), NOW)
    store.delete_user(TENANT, created.id)
    with pytest.raises(ScimError) as exc:
        store.delete_user(TENANT, created.id)
    assert exc.value.status == 404


def test_filter_unsupported_operator_errors() -> None:
    with pytest.raises(ScimError) as exc:
        parse_scim_filter('userName co "alice"')
    assert exc.value.scim_type == "invalidFilter"


def test_filter_eq_with_escaped_quote() -> None:
    f = parse_scim_filter('externalId eq "id-with-\\"-quote"')
    assert f is not None
    assert f.value == 'id-with-"-quote'


def test_tenant_isolation() -> None:
    store = InMemoryScimStore()
    store.create_user("tenant-a", parse_user(_alice()), NOW)
    page, total = store.list_users("tenant-b", None, 1, 50)
    assert total == 0
    assert page == []
