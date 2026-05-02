"""Tests for saml_group_rules — S617.

Coverage:
  * GroupRuleRecord validation rejects blank workspace_id.
  * GroupRuleRecord validation rejects blank group.
  * GroupRuleRecord validation rejects unknown role.
  * GroupRuleRecord accepts all valid roles (owner/admin/editor/operator/viewer).
  * InMemoryGroupRuleStore.list_rules returns empty list for unknown workspace.
  * InMemoryGroupRuleStore.set_rules + list_rules round-trip.
  * set_rules replaces existing rules (not appends).
  * set_rules sorts rules by group name.
  * set_rules raises ValueError on workspace_id mismatch.
  * set_rules raises ValueError on duplicate groups.
  * rules_to_group_role_map converts rules to GroupRoleMapping tuple.
  * rules_to_group_role_map preserves role values for all canonical roles.
  * Integration: rules feed into project_role; owner wins over editor.
  * Integration: rules feed into project_role; default_role returned when no match.
  * Multiple workspaces stored independently.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from loop_control_plane.saml import (
    GroupRoleMapping,
    SamlAssertion,
    SamlSpConfig,
    project_role,
)
from loop_control_plane.saml_group_rules import (
    VALID_ROLES,
    GroupRuleRecord,
    InMemoryGroupRuleStore,
    rules_to_group_role_map,
)

_NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
_WS = "ws-test-123"


def _assertion(groups: list[str]) -> SamlAssertion:
    return SamlAssertion(
        subject="alice@example.com",
        issuer="https://idp.example.com/entity",
        audience=f"https://app.loop.dev/auth/saml/sp/{_WS}",
        not_before=_NOW - timedelta(minutes=5),
        not_on_or_after=_NOW + timedelta(hours=8),
        attributes={"groups": groups},
    )


def _sp_config(rules: list[GroupRuleRecord], default_role: str = "viewer") -> SamlSpConfig:
    return SamlSpConfig(
        sp_entity_id=f"https://app.loop.dev/auth/saml/sp/{_WS}",
        acs_url=f"https://app.loop.dev/auth/saml/acs/{_WS}",
        issuer="https://idp.example.com/entity",
        default_role=default_role,
        group_role_map=rules_to_group_role_map(rules),
        sandbox_mode=False,
    )


# ---------------------------------------------------------------------------
# GroupRuleRecord validation
# ---------------------------------------------------------------------------


def test_group_rule_record_rejects_blank_workspace_id() -> None:
    with pytest.raises(ValueError, match="workspace_id"):
        GroupRuleRecord("", "admins", "admin")


def test_group_rule_record_rejects_blank_group() -> None:
    with pytest.raises(ValueError, match="group"):
        GroupRuleRecord(_WS, "", "admin")


def test_group_rule_record_rejects_unknown_role() -> None:
    with pytest.raises(ValueError, match="role"):
        GroupRuleRecord(_WS, "admins", "superuser")


@pytest.mark.parametrize("role", sorted(VALID_ROLES))
def test_group_rule_record_accepts_all_valid_roles(role: str) -> None:
    record = GroupRuleRecord(_WS, "g", role)
    assert record.role == role


# ---------------------------------------------------------------------------
# InMemoryGroupRuleStore
# ---------------------------------------------------------------------------


def test_list_rules_returns_empty_for_unknown_workspace() -> None:
    store = InMemoryGroupRuleStore()
    assert store.list_rules("ws-unknown") == []


def test_set_rules_and_list_rules_round_trip() -> None:
    store = InMemoryGroupRuleStore()
    rules = [
        GroupRuleRecord(_WS, "admins", "admin"),
        GroupRuleRecord(_WS, "editors", "editor"),
    ]
    store.set_rules(_WS, rules)
    result = store.list_rules(_WS)
    assert len(result) == 2
    assert all(isinstance(r, GroupRuleRecord) for r in result)


def test_set_rules_replaces_existing_rules() -> None:
    store = InMemoryGroupRuleStore()
    store.set_rules(_WS, [GroupRuleRecord(_WS, "old-group", "viewer")])
    store.set_rules(_WS, [GroupRuleRecord(_WS, "new-group", "admin")])
    result = store.list_rules(_WS)
    assert len(result) == 1
    assert result[0].group == "new-group"


def test_set_rules_sorts_by_group_name() -> None:
    store = InMemoryGroupRuleStore()
    store.set_rules(
        _WS,
        [
            GroupRuleRecord(_WS, "zulu", "viewer"),
            GroupRuleRecord(_WS, "alpha", "admin"),
            GroupRuleRecord(_WS, "mike", "editor"),
        ],
    )
    groups = [r.group for r in store.list_rules(_WS)]
    assert groups == sorted(groups)


def test_set_rules_raises_on_workspace_id_mismatch() -> None:
    store = InMemoryGroupRuleStore()
    with pytest.raises(ValueError, match="workspace_id"):
        store.set_rules(_WS, [GroupRuleRecord("ws-other", "admins", "admin")])


def test_set_rules_raises_on_duplicate_groups() -> None:
    store = InMemoryGroupRuleStore()
    with pytest.raises(ValueError, match="Duplicate"):
        store.set_rules(
            _WS,
            [
                GroupRuleRecord(_WS, "admins", "admin"),
                GroupRuleRecord(_WS, "admins", "editor"),
            ],
        )


# ---------------------------------------------------------------------------
# rules_to_group_role_map
# ---------------------------------------------------------------------------


def test_rules_to_group_role_map_converts_records() -> None:
    rules = [
        GroupRuleRecord(_WS, "admins", "admin"),
        GroupRuleRecord(_WS, "viewers", "viewer"),
    ]
    mapping = rules_to_group_role_map(rules)
    assert isinstance(mapping, tuple)
    assert len(mapping) == 2
    assert all(isinstance(m, GroupRoleMapping) for m in mapping)


def test_rules_to_group_role_map_preserves_all_canonical_roles() -> None:
    rules = [
        GroupRuleRecord(_WS, "owners", "owner"),
        GroupRuleRecord(_WS, "admins", "admin"),
        GroupRuleRecord(_WS, "editors", "editor"),
        GroupRuleRecord(_WS, "operators", "operator"),
        GroupRuleRecord(_WS, "viewers", "viewer"),
    ]
    mapping = rules_to_group_role_map(rules)
    roles = {m.role for m in mapping}
    assert roles == {"owner", "admin", "editor", "operator", "viewer"}


# ---------------------------------------------------------------------------
# Integration: rules → project_role
# ---------------------------------------------------------------------------


def test_owner_wins_over_editor_via_project_role() -> None:
    rules = [
        GroupRuleRecord(_WS, "owners", "owner"),
        GroupRuleRecord(_WS, "editors", "editor"),
    ]
    sp = _sp_config(rules, default_role="viewer")
    assertion = _assertion(["editors", "owners"])
    assert project_role(assertion, sp) == "owner"


def test_default_role_returned_when_no_group_matches() -> None:
    rules = [GroupRuleRecord(_WS, "admins", "admin")]
    sp = _sp_config(rules, default_role="operator")
    assertion = _assertion(["other-group"])
    assert project_role(assertion, sp) == "operator"


# ---------------------------------------------------------------------------
# Multiple workspaces
# ---------------------------------------------------------------------------


def test_multiple_workspaces_stored_independently() -> None:
    store = InMemoryGroupRuleStore()
    store.set_rules("ws-a", [GroupRuleRecord("ws-a", "admins", "admin")])
    store.set_rules("ws-b", [GroupRuleRecord("ws-b", "viewers", "viewer")])

    assert store.list_rules("ws-a")[0].group == "admins"
    assert store.list_rules("ws-b")[0].group == "viewers"
