"""Tests for just-in-time user provisioning — S616.

Coverage:
  * New user is created when subject is unknown.
  * Existing user is returned without a second create call.
  * workspace_members row is created with role projected from group claims.
  * workspace_members row is upserted (role refreshed) when membership exists.
  * Default role applied when no group claim matches the map.
  * Multiple groups — first match in assertion order wins.
  * Email attribute preferred over subject when present.
  * Display name derived from SAML attributes when present.
  * Display name is empty string when no name attribute is present.
  * Role refresh: role changes on next login when group mapping changes.
  * Full integration: provision_jit result has correct created_user flag.
  * Full integration: provision_jit result has correct created_membership flag.
  * InMemoryUserStore.create raises ValueError on duplicate sub.
  * InMemoryMembershipStore upsert returns created=False on second call.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from loop_control_plane.jit_provisioning import (
    InMemoryMembershipStore,
    InMemoryUserStore,
    JitProvisioningResult,
    provision_jit,
)
from loop_control_plane.saml import (
    GroupRoleMapping,
    SamlAssertion,
    SamlSpConfig,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_WORKSPACE_ID = "ws-jit-test"
_NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


def _sp_config(
    *,
    default_role: str = "viewer",
    group_role_map: dict[str, str] | None = None,
) -> SamlSpConfig:
    grm = tuple(GroupRoleMapping(group=g, role=r) for g, r in (group_role_map or {}).items())
    return SamlSpConfig(
        sp_entity_id=f"https://app.loop.dev/auth/saml/sp/{_WORKSPACE_ID}",
        acs_url=f"https://app.loop.dev/auth/saml/acs/{_WORKSPACE_ID}",
        issuer="https://idp.example.com/entity",
        default_role=default_role,
        group_role_map=grm,
        sandbox_mode=False,
    )


def _assertion(
    subject: str = "alice@example.com",
    groups: list[str] | None = None,
    extra_attributes: dict[str, list[str]] | None = None,
) -> SamlAssertion:
    attrs: dict[str, list[str]] = {"groups": groups or []}
    if extra_attributes:
        attrs.update(extra_attributes)
    return SamlAssertion(
        subject=subject,
        issuer="https://idp.example.com/entity",
        audience=f"https://app.loop.dev/auth/saml/sp/{_WORKSPACE_ID}",
        not_before=_NOW - timedelta(minutes=5),
        not_on_or_after=_NOW + timedelta(hours=8),
        attributes=attrs,
    )


# ---------------------------------------------------------------------------
# InMemoryUserStore unit tests
# ---------------------------------------------------------------------------


def test_user_store_create_and_get() -> None:
    store = InMemoryUserStore()
    user = store.create("alice@example.com", "alice@example.com", "Alice")
    assert user.sub == "alice@example.com"
    assert user.email == "alice@example.com"
    assert user.display_name == "Alice"
    assert store.get_by_sub("alice@example.com") is user


def test_user_store_get_missing_returns_none() -> None:
    store = InMemoryUserStore()
    assert store.get_by_sub("nobody@example.com") is None


def test_user_store_create_duplicate_raises() -> None:
    store = InMemoryUserStore()
    store.create("alice@example.com", "alice@example.com", "")
    with pytest.raises(ValueError, match="already exists"):
        store.create("alice@example.com", "alice@example.com", "")


# ---------------------------------------------------------------------------
# InMemoryMembershipStore unit tests
# ---------------------------------------------------------------------------


def test_membership_store_upsert_creates_new_row() -> None:
    store = InMemoryMembershipStore()
    membership, created = store.upsert(_WORKSPACE_ID, "alice@example.com", "admin")
    assert created is True
    assert membership.role == "admin"
    assert membership.workspace_id == _WORKSPACE_ID


def test_membership_store_upsert_returns_created_false_on_second_call() -> None:
    store = InMemoryMembershipStore()
    store.upsert(_WORKSPACE_ID, "alice@example.com", "admin")
    _, created = store.upsert(_WORKSPACE_ID, "alice@example.com", "editor")
    assert created is False


def test_membership_store_get_returns_none_when_absent() -> None:
    store = InMemoryMembershipStore()
    assert store.get(_WORKSPACE_ID, "nobody@example.com") is None


# ---------------------------------------------------------------------------
# provision_jit — user creation path
# ---------------------------------------------------------------------------


def test_new_user_created_when_subject_unknown() -> None:
    users = InMemoryUserStore()
    memberships = InMemoryMembershipStore()
    sp = _sp_config()
    assertion = _assertion()

    result = provision_jit(
        assertion,
        sp,
        workspace_id=_WORKSPACE_ID,
        user_store=users,
        membership_store=memberships,
    )

    assert isinstance(result, JitProvisioningResult)
    assert result.created_user is True
    assert result.user.sub == "alice@example.com"
    assert len(users.all()) == 1


def test_existing_user_returned_without_new_create() -> None:
    users = InMemoryUserStore()
    memberships = InMemoryMembershipStore()
    sp = _sp_config()
    assertion = _assertion()

    # Prime the store
    users.create("alice@example.com", "alice@example.com", "Alice")

    result = provision_jit(
        assertion,
        sp,
        workspace_id=_WORKSPACE_ID,
        user_store=users,
        membership_store=memberships,
    )

    assert result.created_user is False
    assert result.user.sub == "alice@example.com"
    assert len(users.all()) == 1  # no duplicate


# ---------------------------------------------------------------------------
# provision_jit — membership creation path
# ---------------------------------------------------------------------------


def test_membership_created_with_role_from_group_claims() -> None:
    users = InMemoryUserStore()
    memberships = InMemoryMembershipStore()
    sp = _sp_config(group_role_map={"admins": "admin", "editors": "editor"})
    assertion = _assertion(groups=["admins"])

    result = provision_jit(
        assertion,
        sp,
        workspace_id=_WORKSPACE_ID,
        user_store=users,
        membership_store=memberships,
    )

    assert result.created_membership is True
    assert result.membership.role == "admin"
    assert result.membership.workspace_id == _WORKSPACE_ID


def test_membership_upserted_on_second_login() -> None:
    users = InMemoryUserStore()
    memberships = InMemoryMembershipStore()
    sp = _sp_config(group_role_map={"admins": "admin"})
    assertion = _assertion(groups=["admins"])

    # First login
    provision_jit(
        assertion, sp, workspace_id=_WORKSPACE_ID, user_store=users, membership_store=memberships
    )

    # Second login — same user, same group
    result = provision_jit(
        assertion, sp, workspace_id=_WORKSPACE_ID, user_store=users, membership_store=memberships
    )

    assert result.created_membership is False
    assert result.membership.role == "admin"


def test_default_role_when_no_group_matches() -> None:
    users = InMemoryUserStore()
    memberships = InMemoryMembershipStore()
    sp = _sp_config(default_role="viewer", group_role_map={"admins": "admin"})
    assertion = _assertion(groups=["other-group"])

    result = provision_jit(
        assertion,
        sp,
        workspace_id=_WORKSPACE_ID,
        user_store=users,
        membership_store=memberships,
    )

    assert result.membership.role == "viewer"


def test_default_role_when_no_groups_in_assertion() -> None:
    users = InMemoryUserStore()
    memberships = InMemoryMembershipStore()
    sp = _sp_config(default_role="operator")
    assertion = _assertion(groups=[])

    result = provision_jit(
        assertion,
        sp,
        workspace_id=_WORKSPACE_ID,
        user_store=users,
        membership_store=memberships,
    )

    assert result.membership.role == "operator"


def test_highest_privilege_group_wins() -> None:
    """When multiple groups match, highest privilege wins per project_role semantics."""
    users = InMemoryUserStore()
    memberships = InMemoryMembershipStore()
    # admin > editor in the privilege order
    sp = _sp_config(group_role_map={"editors": "editor", "admins": "admin"})
    # Assertion lists editors before admins — but admin has higher privilege
    assertion = _assertion(groups=["editors", "admins"])

    result = provision_jit(
        assertion,
        sp,
        workspace_id=_WORKSPACE_ID,
        user_store=users,
        membership_store=memberships,
    )

    assert result.membership.role == "admin"


# ---------------------------------------------------------------------------
# provision_jit — email / display name derivation
# ---------------------------------------------------------------------------


def test_email_attribute_preferred_over_subject() -> None:
    users = InMemoryUserStore()
    memberships = InMemoryMembershipStore()
    sp = _sp_config()
    # subject is an opaque NameID; email attribute contains the real address
    assertion = _assertion(
        subject="opaque-nameid-00001",
        extra_attributes={"email": ["bob@corp.example.com"]},
    )

    result = provision_jit(
        assertion,
        sp,
        workspace_id=_WORKSPACE_ID,
        user_store=users,
        membership_store=memberships,
    )

    assert result.user.sub == "opaque-nameid-00001"
    assert result.user.email == "bob@corp.example.com"


def test_display_name_from_attribute() -> None:
    users = InMemoryUserStore()
    memberships = InMemoryMembershipStore()
    sp = _sp_config()
    assertion = _assertion(
        extra_attributes={"displayName": ["Alice Smith"]},
    )

    result = provision_jit(
        assertion,
        sp,
        workspace_id=_WORKSPACE_ID,
        user_store=users,
        membership_store=memberships,
    )

    assert result.user.display_name == "Alice Smith"


def test_display_name_empty_when_no_name_attribute() -> None:
    users = InMemoryUserStore()
    memberships = InMemoryMembershipStore()
    sp = _sp_config()
    assertion = _assertion()  # no name attributes

    result = provision_jit(
        assertion,
        sp,
        workspace_id=_WORKSPACE_ID,
        user_store=users,
        membership_store=memberships,
    )

    assert result.user.display_name == ""


# ---------------------------------------------------------------------------
# Role refresh scenario
# ---------------------------------------------------------------------------


def test_role_refreshed_when_group_changes() -> None:
    """Role is updated on next login when the group mapping changes."""
    users = InMemoryUserStore()
    memberships = InMemoryMembershipStore()

    # First login as editor
    sp_v1 = _sp_config(group_role_map={"team": "editor"})
    assertion = _assertion(groups=["team"])
    provision_jit(
        assertion, sp_v1, workspace_id=_WORKSPACE_ID, user_store=users, membership_store=memberships
    )

    # Admin escalates team to admin role in the config
    sp_v2 = _sp_config(group_role_map={"team": "admin"})
    result = provision_jit(
        assertion, sp_v2, workspace_id=_WORKSPACE_ID, user_store=users, membership_store=memberships
    )

    assert result.membership.role == "admin"
    assert result.created_membership is False  # upserted, not new
