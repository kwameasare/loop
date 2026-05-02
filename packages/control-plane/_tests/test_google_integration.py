"""Google Workspace SAML integration tests — S614.

Tests the full SP↔IdP loop using the fixture metadata in
``packages/control-plane/fixtures/google_idp_metadata.xml``.

Structure mirrors test_okta_integration.py (S612) and
test_entra_integration.py (S613).

Google Workspace-specific coverage:
  * entityID uses the ``https://accounts.google.com/o/saml2?idpid=<ID>`` form.
  * SSO URL contains ``accounts.google.com``.
  * Google group claims are typically email addresses such as
    ``loop-admins@corp.example.com``.
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
from loop_control_plane.saml_google import (
    GoogleMetadataError,
    GoogleMetadataParser,
    IdPMetadata,
)

# ---------------------------------------------------------------------------
# Fixture file path
# ---------------------------------------------------------------------------

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"
_GOOGLE_METADATA = _FIXTURES / "google_idp_metadata.xml"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TENANT_ID = "ws_google_sandbox"
_NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
# Google group claims are typically email addresses
_ADMIN_GROUP = "loop-admins@corp.example.com"
_EDITOR_GROUP = "loop-editors@corp.example.com"


def _stub_envelope(
    *,
    subject: str = "carol@corp.example.com",
    issuer: str = "https://accounts.google.com/o/saml2?idpid=SandboxGoogleAppID0000",
    audience: str | None = None,
    groups: list[str] | None = None,
    not_before: datetime | None = None,
    not_on_or_after: datetime | None = None,
) -> str:
    """Build a base64-encoded JSON envelope for StubSamlValidator."""
    if audience is None:
        audience = f"https://app.loop.dev/auth/saml/sp/{_TENANT_ID}"
    payload = {
        "subject": subject,
        "issuer": issuer,
        "audience": audience,
        "not_before": (not_before or (_NOW - timedelta(minutes=5))).isoformat(),
        "not_on_or_after": (not_on_or_after or (_NOW + timedelta(hours=8))).isoformat(),
        "attributes": {"groups": groups or [_ADMIN_GROUP]},
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


# ---------------------------------------------------------------------------
# Metadata parser tests
# ---------------------------------------------------------------------------


def test_fixture_file_exists() -> None:
    assert _GOOGLE_METADATA.exists(), (
        f"Google Workspace fixture not found at {_GOOGLE_METADATA}; "
        "the file must be committed at "
        "packages/control-plane/fixtures/google_idp_metadata.xml"
    )


def test_parse_google_fixture_metadata() -> None:
    xml_bytes = _GOOGLE_METADATA.read_bytes()
    parser = GoogleMetadataParser()
    idp = parser.parse(xml_bytes)

    assert isinstance(idp, IdPMetadata)
    assert "accounts.google.com" in idp.entity_id
    assert "accounts.google.com" in idp.sso_url_post
    assert idp.sso_url_redirect is not None
    assert len(idp.cert_pem_chain) >= 1
    assert "BEGIN CERTIFICATE" in idp.cert_pem_chain[0]


def test_parse_produces_correct_sp_entity_id() -> None:
    xml_bytes = _GOOGLE_METADATA.read_bytes()
    idp = GoogleMetadataParser().parse(xml_bytes)
    cfg, _bundle = idp.to_sp_config(_TENANT_ID, sandbox_mode=True)
    assert cfg.sp_entity_id == f"https://app.loop.dev/auth/saml/sp/{_TENANT_ID}"
    assert cfg.acs_url == f"https://app.loop.dev/auth/saml/acs/{_TENANT_ID}"


def test_parse_produces_correct_issuer() -> None:
    xml_bytes = _GOOGLE_METADATA.read_bytes()
    idp = GoogleMetadataParser().parse(xml_bytes)
    cfg, _ = idp.to_sp_config(_TENANT_ID, sandbox_mode=True)
    assert "accounts.google.com" in cfg.issuer


def test_parse_group_role_map_populated() -> None:
    xml_bytes = _GOOGLE_METADATA.read_bytes()
    idp = GoogleMetadataParser().parse(xml_bytes)
    cfg, _ = idp.to_sp_config(
        _TENANT_ID,
        sandbox_mode=True,
        group_role_map={
            _ADMIN_GROUP: "admin",
            "loop-viewers@corp.example.com": "viewer",
        },
    )
    roles = {m.group: m.role for m in cfg.group_role_map}
    assert roles[_ADMIN_GROUP] == "admin"
    assert roles["loop-viewers@corp.example.com"] == "viewer"


def test_metadata_cert_in_bundle() -> None:
    xml_bytes = _GOOGLE_METADATA.read_bytes()
    idp = GoogleMetadataParser().parse(xml_bytes)
    _, bundle = idp.to_sp_config(_TENANT_ID, sandbox_mode=True)
    assert bundle.active_pem.startswith("-----BEGIN CERTIFICATE-----")


def test_parse_error_on_malformed_xml() -> None:
    with pytest.raises(GoogleMetadataError, match="malformed"):
        GoogleMetadataParser().parse(b"<not valid xml")


def test_parse_error_on_missing_entity_id() -> None:
    xml = b"""<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata">
  <md:IDPSSODescriptor
    protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:KeyDescriptor use="signing">
      <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
        <ds:X509Data><ds:X509Certificate>AAAA</ds:X509Certificate></ds:X509Data>
      </ds:KeyInfo>
    </md:KeyDescriptor>
    <md:SingleSignOnService
      Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
      Location="https://accounts.google.com/o/saml2/idp?idpid=x"/>
  </md:IDPSSODescriptor>
</md:EntityDescriptor>"""
    with pytest.raises(GoogleMetadataError, match="entityID"):
        GoogleMetadataParser().parse(xml)


def test_parse_error_on_missing_sso_post_binding() -> None:
    xml = b"""<?xml version="1.0"?>
<md:EntityDescriptor
  xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
  entityID="https://accounts.google.com/o/saml2?idpid=x">
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
      Location="https://accounts.google.com/o/saml2/idp?idpid=x"/>
  </md:IDPSSODescriptor>
</md:EntityDescriptor>"""
    with pytest.raises(GoogleMetadataError, match="HTTP-POST"):
        GoogleMetadataParser().parse(xml)


# ---------------------------------------------------------------------------
# Full SP<->IdP loop (sandbox mode via StubSamlValidator)
# ---------------------------------------------------------------------------


@pytest.fixture
def google_sp() -> tuple[SamlSpConfig, CertificateBundle]:
    xml_bytes = _GOOGLE_METADATA.read_bytes()
    idp = GoogleMetadataParser().parse(xml_bytes)
    return idp.to_sp_config(
        _TENANT_ID,
        sandbox_mode=True,
        group_role_map={_ADMIN_GROUP: "admin", _EDITOR_GROUP: "editor"},
    )


def test_full_acs_loop_happy_path(
    google_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = google_sp
    result = accept_acs_post(_stub_envelope(), cfg, bundle, StubSamlValidator(), now=_NOW)
    assert isinstance(result, AcsResult)
    assert result.assertion.subject == "carol@corp.example.com"


def test_full_acs_loop_role_projected_admin(
    google_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = google_sp
    result = accept_acs_post(
        _stub_envelope(groups=[_ADMIN_GROUP]),
        cfg,
        bundle,
        StubSamlValidator(),
        now=_NOW,
    )
    assert result.role == "admin"


def test_full_acs_loop_role_projected_editor(
    google_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = google_sp
    result = accept_acs_post(
        _stub_envelope(groups=[_EDITOR_GROUP]),
        cfg,
        bundle,
        StubSamlValidator(),
        now=_NOW,
    )
    assert result.role == "editor"


def test_full_acs_loop_default_role_no_group_match(
    google_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = google_sp
    result = accept_acs_post(
        _stub_envelope(groups=["other-group@corp.example.com"]),
        cfg,
        bundle,
        StubSamlValidator(),
        now=_NOW,
    )
    assert result.role == cfg.default_role


def test_full_acs_loop_issuer_mismatch_rejected(
    google_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = google_sp
    with pytest.raises(SamlError, match="issuer"):
        accept_acs_post(
            _stub_envelope(issuer="https://evil.com/saml"),
            cfg,
            bundle,
            StubSamlValidator(),
            now=_NOW,
        )


def test_full_acs_loop_audience_mismatch_rejected(
    google_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = google_sp
    with pytest.raises(SamlError, match="audience"):
        accept_acs_post(
            _stub_envelope(audience="https://other-sp.example.com/sp"),
            cfg,
            bundle,
            StubSamlValidator(),
            now=_NOW,
        )


def test_full_acs_loop_expired_assertion_rejected(
    google_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = google_sp
    past = _NOW - timedelta(hours=2)
    with pytest.raises(SamlError, match="expired"):
        accept_acs_post(
            _stub_envelope(not_before=past - timedelta(hours=1), not_on_or_after=past),
            cfg,
            bundle,
            StubSamlValidator(),
            now=_NOW,
        )
