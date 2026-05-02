"""Okta SAML integration tests — S612.

Tests the full SP↔IdP loop using the fixture metadata in
``packages/control-plane/fixtures/okta_idp_metadata.xml``.

The "integration" aspect here is:
  1. Parse real Okta-schema metadata XML from the fixture file.
  2. Build a SamlSpConfig + CertificateBundle from the parsed metadata.
  3. Drive ``accept_acs_post`` with the ``StubSamlValidator`` (sandbox mode)
     to prove the full ACS validation pipeline works end-to-end.

A true Okta sandbox ↔ live HTTP roundtrip is intentionally out-of-scope
for CI (it requires a live Okta org); the note in S612's AC says
"full SP↔IdP loop in integration" — we satisfy that by wiring the
complete control-plane SP pipeline against the fixture metadata.
"""

from __future__ import annotations

import base64
import json
import pathlib
from datetime import UTC, datetime, timedelta

import pytest
from loop_control_plane.saml import (
    AcsResult,
    SamlError,
    SamlSpConfig,
    StubSamlValidator,
    accept_acs_post,
)
from loop_control_plane.saml_certs import CertificateBundle
from loop_control_plane.saml_okta import IdPMetadata, OktaMetadataError, OktaMetadataParser

# ---------------------------------------------------------------------------
# Fixture file path
# ---------------------------------------------------------------------------

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"
_OKTA_METADATA = _FIXTURES / "okta_idp_metadata.xml"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TENANT_ID = "ws_okta_sandbox"
_NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


def _stub_envelope(
    *,
    subject: str = "alice@example.com",
    issuer: str = "http://www.okta.com/sandbox_loop_test_idp",
    audience: str | None = None,
    groups: list[str] | None = None,
    not_before: datetime | None = None,
    not_on_or_after: datetime | None = None,
) -> str:
    """Build a base64-encoded JSON envelope accepted by StubSamlValidator."""
    if audience is None:
        audience = f"https://app.loop.dev/auth/saml/sp/{_TENANT_ID}"
    payload = {
        "subject": subject,
        "issuer": issuer,
        "audience": audience,
        "not_before": (not_before or (_NOW - timedelta(minutes=5))).isoformat(),
        "not_on_or_after": (not_on_or_after or (_NOW + timedelta(hours=8))).isoformat(),
        "attributes": {"groups": groups or ["Loop-Admins"]},
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


# ---------------------------------------------------------------------------
# Metadata parser tests
# ---------------------------------------------------------------------------


def test_fixture_file_exists() -> None:
    assert _OKTA_METADATA.exists(), (
        f"Okta fixture not found at {_OKTA_METADATA}; "
        "the file must be committed at packages/control-plane/fixtures/okta_idp_metadata.xml"
    )


def test_parse_okta_fixture_metadata() -> None:
    xml_bytes = _OKTA_METADATA.read_bytes()
    parser = OktaMetadataParser()
    idp = parser.parse(xml_bytes)

    assert isinstance(idp, IdPMetadata)
    assert idp.entity_id == "http://www.okta.com/sandbox_loop_test_idp"
    assert "sandbox.okta.com" in idp.sso_url_post
    assert idp.sso_url_redirect is not None
    assert len(idp.cert_pem_chain) >= 1
    assert "BEGIN CERTIFICATE" in idp.cert_pem_chain[0]


def test_parse_produces_correct_sp_entity_id() -> None:
    xml_bytes = _OKTA_METADATA.read_bytes()
    idp = OktaMetadataParser().parse(xml_bytes)
    cfg, _bundle = idp.to_sp_config(_TENANT_ID, sandbox_mode=True)
    assert cfg.sp_entity_id == f"https://app.loop.dev/auth/saml/sp/{_TENANT_ID}"
    assert cfg.acs_url == f"https://app.loop.dev/auth/saml/acs/{_TENANT_ID}"


def test_parse_produces_correct_issuer() -> None:
    xml_bytes = _OKTA_METADATA.read_bytes()
    idp = OktaMetadataParser().parse(xml_bytes)
    cfg, _ = idp.to_sp_config(_TENANT_ID, sandbox_mode=True)
    assert cfg.issuer == "http://www.okta.com/sandbox_loop_test_idp"


def test_parse_group_role_map_populated() -> None:
    xml_bytes = _OKTA_METADATA.read_bytes()
    idp = OktaMetadataParser().parse(xml_bytes)
    cfg, _ = idp.to_sp_config(
        _TENANT_ID,
        sandbox_mode=True,
        group_role_map={"Loop-Admins": "admin", "Loop-Viewers": "viewer"},
    )
    roles = {m.group: m.role for m in cfg.group_role_map}
    assert roles["Loop-Admins"] == "admin"
    assert roles["Loop-Viewers"] == "viewer"


def test_metadata_cert_in_bundle() -> None:
    xml_bytes = _OKTA_METADATA.read_bytes()
    idp = OktaMetadataParser().parse(xml_bytes)
    _, bundle = idp.to_sp_config(_TENANT_ID, sandbox_mode=True)
    assert bundle.active_pem.startswith("-----BEGIN CERTIFICATE-----")


def test_parse_error_on_malformed_xml() -> None:
    with pytest.raises(OktaMetadataError, match="malformed"):
        OktaMetadataParser().parse(b"<not valid xml")


def test_parse_error_on_missing_entity_id() -> None:
    xml = b"""<?xml version="1.0"?>
<md:EntityDescriptor
  xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata">
  <md:IDPSSODescriptor
    protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:KeyDescriptor use="signing">
      <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
        <ds:X509Data><ds:X509Certificate>AAAA</ds:X509Certificate></ds:X509Data>
      </ds:KeyInfo>
    </md:KeyDescriptor>
    <md:SingleSignOnService
      Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
      Location="https://idp.example.com/sso"/>
  </md:IDPSSODescriptor>
</md:EntityDescriptor>"""
    with pytest.raises(OktaMetadataError, match="entityID"):
        OktaMetadataParser().parse(xml)


def test_parse_error_on_missing_sso_post_binding() -> None:
    xml = b"""<?xml version="1.0"?>
<md:EntityDescriptor
  xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
  entityID="https://idp.example.com">
  <md:IDPSSODescriptor
    protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:KeyDescriptor use="signing">
      <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
        <ds:X509Data><ds:X509Certificate>AAAA</ds:X509Certificate></ds:X509Data>
      </ds:KeyInfo>
    </md:KeyDescriptor>
    <!-- Only redirect; POST is missing -->
    <md:SingleSignOnService
      Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
      Location="https://idp.example.com/sso"/>
  </md:IDPSSODescriptor>
</md:EntityDescriptor>"""
    with pytest.raises(OktaMetadataError, match="HTTP-POST"):
        OktaMetadataParser().parse(xml)


# ---------------------------------------------------------------------------
# Full SP↔IdP loop (sandbox mode via StubSamlValidator)
# ---------------------------------------------------------------------------


@pytest.fixture
def okta_sp() -> tuple[SamlSpConfig, CertificateBundle]:
    xml_bytes = _OKTA_METADATA.read_bytes()
    idp = OktaMetadataParser().parse(xml_bytes)
    return idp.to_sp_config(
        _TENANT_ID,
        sandbox_mode=True,
        group_role_map={"Loop-Admins": "admin", "Loop-Editors": "editor"},
    )


def test_full_acs_loop_happy_path(
    okta_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = okta_sp
    validator = StubSamlValidator()
    response = _stub_envelope()
    result = accept_acs_post(response, cfg, bundle, validator, now=_NOW)
    assert isinstance(result, AcsResult)
    assert result.assertion.subject == "alice@example.com"


def test_full_acs_loop_role_projected_admin(
    okta_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = okta_sp
    result = accept_acs_post(
        _stub_envelope(groups=["Loop-Admins"]),
        cfg,
        bundle,
        StubSamlValidator(),
        now=_NOW,
    )
    assert result.role == "admin"


def test_full_acs_loop_role_projected_editor(
    okta_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = okta_sp
    result = accept_acs_post(
        _stub_envelope(groups=["Loop-Editors"]),
        cfg,
        bundle,
        StubSamlValidator(),
        now=_NOW,
    )
    assert result.role == "editor"


def test_full_acs_loop_default_role_no_group_match(
    okta_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = okta_sp
    result = accept_acs_post(
        _stub_envelope(groups=["Unknown-Group"]),
        cfg,
        bundle,
        StubSamlValidator(),
        now=_NOW,
    )
    assert result.role == cfg.default_role


def test_full_acs_loop_issuer_mismatch_rejected(
    okta_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = okta_sp
    response = _stub_envelope(issuer="https://evil.com/saml")
    with pytest.raises(SamlError, match="issuer"):
        accept_acs_post(response, cfg, bundle, StubSamlValidator(), now=_NOW)


def test_full_acs_loop_audience_mismatch_rejected(
    okta_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = okta_sp
    response = _stub_envelope(audience="https://other-sp.example.com/sp")
    with pytest.raises(SamlError, match="audience"):
        accept_acs_post(response, cfg, bundle, StubSamlValidator(), now=_NOW)


def test_full_acs_loop_expired_assertion_rejected(
    okta_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = okta_sp
    past = _NOW - timedelta(hours=2)
    response = _stub_envelope(not_before=past - timedelta(hours=1), not_on_or_after=past)
    with pytest.raises(SamlError, match="expired"):
        accept_acs_post(response, cfg, bundle, StubSamlValidator(), now=_NOW)
