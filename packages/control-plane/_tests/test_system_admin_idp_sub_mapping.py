"""Regression test for :func:`_system_admin_context` IdP-sub mapping.

The PASETO access-token's ``sub`` claim is the UUID5 mapping of the
caller's raw IdP sub (Auth0, Google, Okta, …). Operators paste the
raw form into ``LOOP_SYSTEM_ADMIN_SUBS`` because that's what every
IdP dashboard surfaces, but the runtime check sees the mapped form.
Without the dual-form match, the system-admin route would 403 every
real Auth0-backed admin. This test pins both directions.
"""

from __future__ import annotations

import pytest

from loop_control_plane._routes_enterprise_admin import _system_admin_context
from loop_control_plane.auth_exchange import map_idp_sub_to_internal_user_id
from loop_control_plane.authorize import AuthorisationError


def test_raw_idp_sub_in_env_matches_mapped_caller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Operator pastes ``google-oauth2|123``; PASETO caller sub is the
    UUID5 of that. Both must be admitted."""
    raw_sub = "google-oauth2|116694504926445977501"
    mapped = map_idp_sub_to_internal_user_id(raw_sub)
    monkeypatch.setenv("LOOP_SYSTEM_ADMIN_SUBS", raw_sub)
    context = _system_admin_context(mapped)
    assert context["mode"] == "configured"
    assert context["actor_sub"] == mapped


def test_mapped_internal_sub_in_env_also_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Operator who already knows the internal UUID5 can paste that
    too (the existing test suite uses raw plaintext subs)."""
    raw_sub = "auth0|user-abc"
    mapped = map_idp_sub_to_internal_user_id(raw_sub)
    monkeypatch.setenv("LOOP_SYSTEM_ADMIN_SUBS", mapped)
    context = _system_admin_context(mapped)
    assert context["mode"] == "configured"


def test_non_admin_caller_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOOP_SYSTEM_ADMIN_SUBS", "auth0|admin-only")
    with pytest.raises(AuthorisationError, match="system admin role required"):
        _system_admin_context("auth0|some-other-user")


def test_comma_separated_admins_all_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_a = "google-oauth2|111"
    raw_b = "auth0|222"
    monkeypatch.setenv("LOOP_SYSTEM_ADMIN_SUBS", f"{raw_a},{raw_b}")
    # Both mapped forms should be admitted.
    for raw in (raw_a, raw_b):
        context = _system_admin_context(map_idp_sub_to_internal_user_id(raw))
        assert context["mode"] == "configured"
