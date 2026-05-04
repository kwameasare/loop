"""Tests for JIT user provisioning — S616.

Coverage:
- Unknown subject → creates user + workspace_members row, role from group mapping.
- Repeat login → reuses user row, no duplicate member, role-changed flag.
- Email collision under different IdP subject → JitCollisionError.
- Default-role fallback when no group matches.
- Display-name extraction from common SAML attributes.
- WS-Federation email claim shape (Entra ID).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from loop_control_plane.saml import (
    AcsResult,
    GroupRoleMapping,
    SamlAssertion,
    SamlSpConfig,
    project_role,
)
from loop_control_plane.saml_jit import (
    InMemoryUserStore,
    JitCollisionError,
    JitProvisionError,
    jit_provision,
)

_NOW = datetime(2027, 4, 1, 12, 0, 0, tzinfo=UTC)


def _assertion(
    *,
    subject: str = "alice@acme.example",
    issuer: str = "https://idp.example/sso",
    audience: str = "loop:tenant:t1",
    attributes: dict[str, list[str]] | None = None,
) -> SamlAssertion:
    return SamlAssertion(
        subject=subject,
        issuer=issuer,
        audience=audience,
        not_before=_NOW - timedelta(minutes=1),
        not_on_or_after=_NOW + timedelta(minutes=10),
        attributes=attributes or {"groups": ["loop-admins"], "email": [subject]},
    )


def _sp(
    *,
    default_role: str = "viewer",
    map_: tuple[GroupRoleMapping, ...] = (
        GroupRoleMapping(group="loop-admins", role="admin"),
        GroupRoleMapping(group="loop-editors", role="editor"),
    ),
) -> SamlSpConfig:
    return SamlSpConfig(
        sp_entity_id="loop:tenant:t1",
        acs_url="https://cp.example/saml/acs/t1",
        issuer="https://idp.example/sso",
        default_role=default_role,
        group_role_map=map_,
        sandbox_mode=True,
    )


def _acs(assertion: SamlAssertion, sp: SamlSpConfig) -> AcsResult:
    return AcsResult(assertion=assertion, role=project_role(assertion, sp))


def test_unknown_subject_provisions_user_and_member() -> None:
    store = InMemoryUserStore()
    workspace_id = uuid.uuid4()
    sp = _sp()
    acs = _acs(_assertion(), sp)

    result = jit_provision(
        acs,
        workspace_id=workspace_id,
        auth_provider="saml-okta",
        store=store,
        now=_NOW,
    )

    assert result.created_user is True
    assert result.created_member is True
    assert result.role_changed is False
    assert result.user.email == "alice@acme.example"
    assert result.user.auth_provider == "saml-okta"
    assert result.user.auth_subject == "alice@acme.example"
    assert result.member.workspace_id == workspace_id
    assert result.member.user_id == result.user.id
    assert result.member.role == "admin"


def test_repeat_login_reuses_user_no_duplicate_member() -> None:
    store = InMemoryUserStore()
    workspace_id = uuid.uuid4()
    sp = _sp()
    acs = _acs(_assertion(), sp)

    first = jit_provision(
        acs, workspace_id=workspace_id, auth_provider="saml-okta", store=store, now=_NOW
    )
    second = jit_provision(
        acs,
        workspace_id=workspace_id,
        auth_provider="saml-okta",
        store=store,
        now=_NOW + timedelta(hours=1),
    )

    assert second.user.id == first.user.id
    assert second.created_user is False
    assert second.created_member is False
    assert second.role_changed is False


def test_repeat_login_with_changed_groups_updates_role() -> None:
    store = InMemoryUserStore()
    workspace_id = uuid.uuid4()
    sp = _sp()

    first = jit_provision(
        _acs(_assertion(attributes={"groups": ["loop-editors"]}), sp),
        workspace_id=workspace_id,
        auth_provider="saml-okta",
        store=store,
        now=_NOW,
    )
    assert first.member.role == "editor"

    promoted = jit_provision(
        _acs(_assertion(attributes={"groups": ["loop-admins"]}), sp),
        workspace_id=workspace_id,
        auth_provider="saml-okta",
        store=store,
        now=_NOW + timedelta(days=1),
    )
    assert promoted.member.role == "admin"
    assert promoted.created_user is False
    assert promoted.created_member is False
    assert promoted.role_changed is True


def test_email_collision_under_different_subject_raises() -> None:
    store = InMemoryUserStore()
    workspace_id = uuid.uuid4()
    sp = _sp()

    jit_provision(
        _acs(_assertion(subject="alice@acme.example"), sp),
        workspace_id=workspace_id,
        auth_provider="saml-okta",
        store=store,
        now=_NOW,
    )

    # Same email arriving from a different IdP subject (e.g. operator
    # accidentally connected a second IdP that also issues alice's
    # email) MUST NOT silently rebind the existing row.
    sp2 = SamlSpConfig(
        sp_entity_id=sp.sp_entity_id,
        acs_url=sp.acs_url,
        issuer="https://other-idp.example/sso",
        default_role=sp.default_role,
        group_role_map=sp.group_role_map,
        sandbox_mode=True,
    )
    other = SamlAssertion(
        subject="alice-different-subject",
        issuer="https://other-idp.example/sso",
        audience="loop:tenant:t1",
        not_before=_NOW - timedelta(minutes=1),
        not_on_or_after=_NOW + timedelta(minutes=10),
        attributes={"groups": ["loop-admins"], "email": ["alice@acme.example"]},
    )
    with pytest.raises(JitCollisionError, match="reconcile"):
        jit_provision(
            _acs(other, sp2),
            workspace_id=workspace_id,
            auth_provider="saml-google",
            store=store,
            now=_NOW + timedelta(minutes=1),
        )


def test_default_role_when_no_group_matches() -> None:
    store = InMemoryUserStore()
    workspace_id = uuid.uuid4()
    sp = _sp(default_role="viewer")
    acs = _acs(_assertion(attributes={"groups": ["external-vendor"]}), sp)

    result = jit_provision(
        acs,
        workspace_id=workspace_id,
        auth_provider="saml-okta",
        store=store,
        now=_NOW,
    )
    assert result.member.role == "viewer"


def test_display_name_extracted_from_attribute() -> None:
    store = InMemoryUserStore()
    workspace_id = uuid.uuid4()
    sp = _sp()
    acs = _acs(
        _assertion(
            attributes={
                "groups": ["loop-admins"],
                "email": ["alice@acme.example"],
                "displayName": ["Alice Anderson"],
            }
        ),
        sp,
    )

    result = jit_provision(
        acs,
        workspace_id=workspace_id,
        auth_provider="saml-okta",
        store=store,
        now=_NOW,
    )
    assert result.user.full_name == "Alice Anderson"


def test_entra_wsfed_email_claim_shape_recognized() -> None:
    """Entra ID emits the email under the WS-Fed claim URI."""
    store = InMemoryUserStore()
    workspace_id = uuid.uuid4()
    sp = _sp()
    acs = _acs(
        _assertion(
            subject="00000000-0000-0000-0000-000000000abc",
            attributes={
                "groups": ["loop-admins"],
                "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress": [
                    "alice@contoso.example"
                ],
                "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name": [
                    "Alice Contoso"
                ],
            },
        ),
        sp,
    )

    result = jit_provision(
        acs,
        workspace_id=workspace_id,
        auth_provider="saml-entra",
        store=store,
        now=_NOW,
    )
    assert result.user.email == "alice@contoso.example"
    assert result.user.full_name == "Alice Contoso"


def test_invalid_role_raises() -> None:
    store = InMemoryUserStore()
    workspace_id = uuid.uuid4()
    _sp()
    acs = AcsResult(assertion=_assertion(), role="superuser")
    with pytest.raises(JitProvisionError, match="not a valid workspace role"):
        jit_provision(
            acs,
            workspace_id=workspace_id,
            auth_provider="saml-okta",
            store=store,
            now=_NOW,
        )
