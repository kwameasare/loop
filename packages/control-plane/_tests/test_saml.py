"""Tests for SAML SP boundary: ACS handler, validator Protocol, role projection (S610)."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta

import pytest
from loop_control_plane.saml import (
    AcsResult,
    GroupRoleMapping,
    SamlAssertion,
    SamlError,
    SamlSpConfig,
    StubSamlValidator,
    accept_acs_post,
    project_role,
)
from loop_control_plane.saml_certs import CertificateBundle

PEM_A = "-----BEGIN CERTIFICATE-----\nAAA\n-----END CERTIFICATE-----"
NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
SP_ENTITY = "https://app.loop.dev/auth/saml/sp/ws_acme"
IDP_ENTITY = "https://idp.example.com/saml"


def _build_envelope(**overrides: object) -> str:
    payload = {
        "subject": "alice@example.com",
        "issuer": IDP_ENTITY,
        "audience": SP_ENTITY,
        "not_before": (NOW - timedelta(minutes=1)).isoformat(),
        "not_on_or_after": (NOW + timedelta(minutes=10)).isoformat(),
        "attributes": {"groups": ["Loop-Editors"]},
        "session_index": "idx-1",
    }
    payload.update(overrides)
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")


def _sp_config(**overrides: object) -> SamlSpConfig:
    base = {
        "sp_entity_id": SP_ENTITY,
        "acs_url": f"{SP_ENTITY}/acs",
        "issuer": IDP_ENTITY,
        "default_role": "viewer",
        "group_role_map": (
            GroupRoleMapping("Loop-Admins", "admin"),
            GroupRoleMapping("Loop-Editors", "editor"),
        ),
        "sandbox_mode": True,
    }
    base.update(overrides)
    return SamlSpConfig(**base)  # type: ignore[arg-type]


def _bundle() -> CertificateBundle:
    return CertificateBundle(active_pem=PEM_A)


def test_acs_happy_path_returns_assertion_and_role() -> None:
    result = accept_acs_post(
        _build_envelope(),
        _sp_config(),
        _bundle(),
        StubSamlValidator(),
        now=NOW,
    )
    assert isinstance(result, AcsResult)
    assert result.assertion.subject == "alice@example.com"
    assert result.role == "editor"


def test_acs_rejects_audience_mismatch() -> None:
    envelope = _build_envelope(audience="https://other.example.com/sp/x")
    with pytest.raises(SamlError, match="audience"):
        accept_acs_post(envelope, _sp_config(), _bundle(), StubSamlValidator(), now=NOW)


def test_acs_rejects_issuer_mismatch() -> None:
    envelope = _build_envelope(issuer="https://attacker.example.com/")
    with pytest.raises(SamlError, match="issuer"):
        accept_acs_post(envelope, _sp_config(), _bundle(), StubSamlValidator(), now=NOW)


def test_acs_rejects_expired_assertion() -> None:
    envelope = _build_envelope(
        not_before=(NOW - timedelta(hours=2)).isoformat(),
        not_on_or_after=(NOW - timedelta(hours=1)).isoformat(),
    )
    with pytest.raises(SamlError, match="expired"):
        accept_acs_post(envelope, _sp_config(), _bundle(), StubSamlValidator(), now=NOW)


def test_acs_rejects_not_yet_valid_assertion() -> None:
    envelope = _build_envelope(
        not_before=(NOW + timedelta(hours=1)).isoformat(),
        not_on_or_after=(NOW + timedelta(hours=2)).isoformat(),
    )
    with pytest.raises(SamlError, match="not yet valid"):
        accept_acs_post(envelope, _sp_config(), _bundle(), StubSamlValidator(), now=NOW)


def test_acs_clock_skew_tolerance() -> None:
    """Within the configured skew, an assertion that just expired
    is still accepted."""
    just_expired = NOW - timedelta(seconds=30)
    envelope = _build_envelope(
        not_before=(NOW - timedelta(minutes=10)).isoformat(),
        not_on_or_after=just_expired.isoformat(),
    )
    # default clock_skew is 2 minutes -> 30s past expiry is still valid.
    result = accept_acs_post(envelope, _sp_config(), _bundle(), StubSamlValidator(), now=NOW)
    assert result.assertion.subject == "alice@example.com"


def test_acs_rejects_malformed_envelope() -> None:
    bad = base64.b64encode(b"not-json").decode("ascii")
    with pytest.raises(SamlError, match="malformed"):
        accept_acs_post(bad, _sp_config(), _bundle(), StubSamlValidator(), now=NOW)


def test_stub_validator_refuses_non_sandbox_tenant() -> None:
    cfg = _sp_config(sandbox_mode=False)
    with pytest.raises(SamlError, match="sandbox tenants"):
        accept_acs_post(_build_envelope(), cfg, _bundle(), StubSamlValidator(), now=NOW)


def test_stub_validator_refuses_empty_trust_set() -> None:
    bundle = CertificateBundle(active_pem="")
    with pytest.raises(SamlError, match="certificate bundle"):
        accept_acs_post(_build_envelope(), _sp_config(), bundle, StubSamlValidator(), now=NOW)


def test_project_role_picks_highest_privilege_match() -> None:
    """If the IdP releases groups for two mapped roles, we promote."""
    assertion = SamlAssertion(
        subject="alice@example.com",
        issuer=IDP_ENTITY,
        audience=SP_ENTITY,
        not_before=NOW,
        not_on_or_after=NOW + timedelta(hours=1),
        attributes={"groups": ["Loop-Editors", "Loop-Admins"]},
    )
    cfg = _sp_config()
    assert project_role(assertion, cfg) == "admin"


def test_project_role_falls_back_to_default() -> None:
    assertion = SamlAssertion(
        subject="alice@example.com",
        issuer=IDP_ENTITY,
        audience=SP_ENTITY,
        not_before=NOW,
        not_on_or_after=NOW + timedelta(hours=1),
        attributes={"groups": ["Loop-Mystery"]},
    )
    cfg = _sp_config(default_role="viewer")
    assert project_role(assertion, cfg) == "viewer"
