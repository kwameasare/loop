"""Tests for SAML group → role mapping rules — S617.

Coverage:
- upsert/list/delete round-trip
- role validation (rejects invalid roles)
- group_name validation (non-empty, length cap)
- re-upsert preserves row id + created_at, only changes role
- load_group_rules projects to GroupRoleMapping tuple in stable order
- ACS handler uses loaded rules to project owner / editor / viewer
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from loop_control_plane.saml import (
    SamlAssertion,
    SamlSpConfig,
    StubSamlValidator,
    accept_acs_post,
)
from loop_control_plane.saml_certs import CertificateBundle
from loop_control_plane.saml_group_rules import (
    GroupRuleError,
    InMemoryGroupRuleStore,
    delete_group_rule,
    load_group_rules,
    upsert_group_rule,
)


_NOW = datetime(2027, 4, 1, 12, 0, 0, tzinfo=UTC)


def _make_workspace() -> uuid.UUID:
    return uuid.uuid4()


def test_upsert_then_list_round_trip() -> None:
    store = InMemoryGroupRuleStore()
    ws = _make_workspace()
    upsert_group_rule(
        workspace_id=ws, group_name="loop-admins", role="admin", store=store, now=_NOW
    )
    upsert_group_rule(
        workspace_id=ws, group_name="loop-editors", role="editor", store=store, now=_NOW
    )
    rules = store.list_rules(ws)
    assert len(rules) == 2
    assert {(r.group_name, r.role) for r in rules} == {
        ("loop-admins", "admin"),
        ("loop-editors", "editor"),
    }


def test_invalid_role_rejected() -> None:
    store = InMemoryGroupRuleStore()
    with pytest.raises(GroupRuleError, match="not one of"):
        upsert_group_rule(
            workspace_id=_make_workspace(),
            group_name="loop-admins",
            role="superuser",
            store=store,
        )


def test_empty_group_name_rejected() -> None:
    store = InMemoryGroupRuleStore()
    with pytest.raises(GroupRuleError, match="non-empty"):
        upsert_group_rule(
            workspace_id=_make_workspace(),
            group_name="   ",
            role="admin",
            store=store,
        )


def test_group_name_length_cap() -> None:
    store = InMemoryGroupRuleStore()
    long_name = "g" * 257
    with pytest.raises(GroupRuleError, match="character limit"):
        upsert_group_rule(
            workspace_id=_make_workspace(),
            group_name=long_name,
            role="admin",
            store=store,
        )


def test_reupsert_preserves_id_and_created_at() -> None:
    store = InMemoryGroupRuleStore()
    ws = _make_workspace()
    first = upsert_group_rule(
        workspace_id=ws, group_name="loop-admins", role="admin", store=store, now=_NOW
    )
    later = _NOW + timedelta(days=2)
    second = upsert_group_rule(
        workspace_id=ws,
        group_name="loop-admins",
        role="editor",
        store=store,
        now=later,
    )
    assert second.id == first.id
    assert second.created_at == first.created_at
    assert second.role == "editor"


def test_delete_removes_rule() -> None:
    store = InMemoryGroupRuleStore()
    ws = _make_workspace()
    upsert_group_rule(
        workspace_id=ws, group_name="loop-admins", role="admin", store=store, now=_NOW
    )
    assert delete_group_rule(workspace_id=ws, group_name="loop-admins", store=store) is True
    assert delete_group_rule(workspace_id=ws, group_name="loop-admins", store=store) is False
    assert store.list_rules(ws) == ()


def test_load_group_rules_returns_stable_order() -> None:
    store = InMemoryGroupRuleStore()
    ws = _make_workspace()
    for name, role in [
        ("zeta", "viewer"),
        ("alpha", "admin"),
        ("middle", "editor"),
    ]:
        upsert_group_rule(workspace_id=ws, group_name=name, role=role, store=store, now=_NOW)
    rules = load_group_rules(ws, store=store)
    assert [r.group for r in rules] == ["alpha", "middle", "zeta"]


def _bundle() -> CertificateBundle:
    return CertificateBundle(
        active_pem="-----BEGIN CERTIFICATE-----\nSANDBOX\n-----END CERTIFICATE-----\n",
    )


def _envelope(*, groups: list[str]) -> str:
    import base64
    import json

    payload = {
        "subject": "alice@acme.example",
        "issuer": "https://idp.example/sso",
        "audience": "loop:tenant:t1",
        "not_before": (_NOW - timedelta(minutes=1)).isoformat(),
        "not_on_or_after": (_NOW + timedelta(minutes=10)).isoformat(),
        "attributes": {"groups": groups, "email": ["alice@acme.example"]},
    }
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")


@pytest.mark.parametrize(
    "groups, expected_role",
    [
        (["loop-owners"], "owner"),
        (["loop-editors"], "editor"),
        (["external-vendor"], "viewer"),
    ],
)
def test_acs_uses_loaded_rules_for_role_projection(
    groups: list[str], expected_role: str
) -> None:
    store = InMemoryGroupRuleStore()
    ws = _make_workspace()
    upsert_group_rule(
        workspace_id=ws, group_name="loop-owners", role="owner", store=store, now=_NOW
    )
    upsert_group_rule(
        workspace_id=ws, group_name="loop-editors", role="editor", store=store, now=_NOW
    )
    upsert_group_rule(
        workspace_id=ws, group_name="loop-viewers", role="viewer", store=store, now=_NOW
    )

    sp = SamlSpConfig(
        sp_entity_id="loop:tenant:t1",
        acs_url="https://cp.example/saml/acs/t1",
        issuer="https://idp.example/sso",
        default_role="viewer",
        group_role_map=load_group_rules(ws, store=store),
        sandbox_mode=True,
    )
    result = accept_acs_post(
        _envelope(groups=groups),
        sp,
        _bundle(),
        StubSamlValidator(),
        now=_NOW,
    )
    assert result.role == expected_role


def test_isolation_between_workspaces() -> None:
    store = InMemoryGroupRuleStore()
    ws_a = _make_workspace()
    ws_b = _make_workspace()
    upsert_group_rule(
        workspace_id=ws_a, group_name="loop-admins", role="admin", store=store, now=_NOW
    )
    upsert_group_rule(
        workspace_id=ws_b, group_name="loop-admins", role="viewer", store=store, now=_NOW
    )
    assert load_group_rules(ws_a, store=store)[0].role == "admin"
    assert load_group_rules(ws_b, store=store)[0].role == "viewer"
