"""Microsoft Entra ID SAML integration tests — S613.

Tests the full SP↔IdP loop using the fixture metadata in
``packages/control-plane/fixtures/entra_idp_metadata.xml``.

Structure mirrors test_okta_integration.py (S612):
  1. Parse Entra-schema metadata XML from the fixture file.
  2. Build a SamlSpConfig + CertificateBundle via IdPMetadata.to_sp_config().
  3. Drive ``accept_acs_post`` with StubSamlValidator to exercise the full
     ACS pipeline (no live Entra tenant required in CI).

Entra-specific coverage:
  * entityID uses the ``https://sts.windows.net/<tenant-id>/`` form.
  * SSO URL contains ``login.microsoftonline.com``.
  * Metadata uses default namespace (no ``md:`` prefix in raw XML) —
    the parser must handle both prefix styles.
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
from loop_control_plane.saml_entra import EntraMetadataError, EntraMetadataParser, IdPMetadata

# ---------------------------------------------------------------------------
# Fixture file path
# ---------------------------------------------------------------------------

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"
_ENTRA_METADATA = _FIXTURES / "entra_idp_metadata.xml"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TENANT_ID = "ws_entra_sandbox"
_NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


def _stub_envelope(
    *,
    subject: str = "bob@corp.example.com",
    issuer: str = "https://sts.windows.net/sandbox-tenant-id-00000000/",
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
        "attributes": {"groups": groups or ["Loop-Admins"]},
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


# ---------------------------------------------------------------------------
# Metadata parser tests
# ---------------------------------------------------------------------------


def test_fixture_file_exists() -> None:
    assert _ENTRA_METADATA.exists(), (
        f"Entra ID fixture not found at {_ENTRA_METADATA}; "
        "the file must be committed at "
        "packages/control-plane/fixtures/entra_idp_metadata.xml"
    )


def test_parse_entra_fixture_metadata() -> None:
    xml_bytes = _ENTRA_METADATA.read_bytes()
    parser = EntraMetadataParser()
    idp = parser.parse(xml_bytes)

    assert isinstance(idp, IdPMetadata)
    assert idp.entity_id == "https://sts.windows.net/sandbox-tenant-id-00000000/"
    assert "login.microsoftonline.com" in idp.sso_url_post
    assert idp.sso_url_redirect is not None
    assert len(idp.cert_pem_chain) >= 1
    assert "BEGIN CERTIFICATE" in idp.cert_pem_chain[0]


def test_parse_produces_correct_sp_entity_id() -> None:
    xml_bytes = _ENTRA_METADATA.read_bytes()
    idp = EntraMetadataParser().parse(xml_bytes)
    cfg, _bundle = idp.to_sp_config(_TENANT_ID, sandbox_mode=True)
    assert cfg.sp_entity_id == f"https://app.loop.dev/auth/saml/sp/{_TENANT_ID}"
    assert cfg.acs_url == f"https://app.loop.dev/auth/saml/acs/{_TENANT_ID}"


def test_parse_produces_correct_issuer() -> None:
    xml_bytes = _ENTRA_METADATA.read_bytes()
    idp = EntraMetadataParser().parse(xml_bytes)
    cfg, _ = idp.to_sp_config(_TENANT_ID, sandbox_mode=True)
    assert cfg.issuer == "https://sts.windows.net/sandbox-tenant-id-00000000/"


def test_parse_group_role_map_populated() -> None:
    xml_bytes = _ENTRA_METADATA.read_bytes()
    idp = EntraMetadataParser().parse(xml_bytes)
    cfg, _ = idp.to_sp_config(
        _TENANT_ID,
        sandbox_mode=True,
        group_role_map={"Loop-Admins": "admin", "Loop-Viewers": "viewer"},
    )
    roles = {m.group: m.role for m in cfg.group_role_map}
    assert roles["Loop-Admins"] == "admin"
    assert roles["Loop-Viewers"] == "viewer"


def test_metadata_cert_in_bundle() -> None:
    xml_bytes = _ENTRA_METADATA.read_bytes()
    idp = EntraMetadataParser().parse(xml_bytes)
    _, bundle = idp.to_sp_config(_TENANT_ID, sandbox_mode=True)
    assert bundle.active_pem.startswith("-----BEGIN CERTIFICATE-----")


def test_parse_error_on_malformed_xml() -> None:
    with pytest.raises(EntraMetadataError, match="malformed"):
        EntraMetadataParser().parse(b"<not valid xml")


def test_parse_error_on_missing_entity_id() -> None:
    xml = b"""<?xml version="1.0"?>
<EntityDescriptor
  xmlns="urn:oasis:names:tc:SAML:2.0:metadata">
  <IDPSSODescriptor
    protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <KeyDescriptor use="signing">
      <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
        <ds:X509Data><ds:X509Certificate>AAAA</ds:X509Certificate></ds:X509Data>
      </ds:KeyInfo>
    </KeyDescriptor>
    <SingleSignOnService
      Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
      Location="https://login.microsoftonline.com/x/saml2"/>
  </IDPSSODescriptor>
</EntityDescriptor>"""
    with pytest.raises(EntraMetadataError, match="entityID"):
        EntraMetadataParser().parse(xml)


def test_parse_error_on_missing_sso_post_binding() -> None:
    xml = b"""<?xml version="1.0"?>
<EntityDescriptor
  xmlns="urn:oasis:names:tc:SAML:2.0:metadata"
  entityID="https://sts.windows.net/x/">
  <IDPSSODescriptor
    protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <KeyDescriptor use="signing">
      <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
        <ds:X509Data><ds:X509Certificate>AAAA</ds:X509Certificate></ds:X509Data>
      </ds:KeyInfo>
    </KeyDescriptor>
    <!-- Only redirect; POST is missing -->
    <SingleSignOnService
      Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
      Location="https://login.microsoftonline.com/x/saml2"/>
  </IDPSSODescriptor>
</EntityDescriptor>"""
    with pytest.raises(EntraMetadataError, match="HTTP-POST"):
        EntraMetadataParser().parse(xml)


# ---------------------------------------------------------------------------
# Full SP<->IdP loop (sandbox mode via StubSamlValidator)
# ---------------------------------------------------------------------------


@pytest.fixture
def entra_sp() -> tuple[SamlSpConfig, CertificateBundle]:
    xml_bytes = _ENTRA_METADATA.read_bytes()
    idp = EntraMetadataParser().parse(xml_bytes)
    return idp.to_sp_config(
        _TENANT_ID,
        sandbox_mode=True,
        group_role_map={"Loop-Admins": "admin", "Loop-Editors": "editor"},
    )


def test_full_acs_loop_happy_path(
    entra_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = entra_sp
    result = accept_acs_post(_stub_envelope(), cfg, bundle, StubSamlValidator(), now=_NOW)
    assert isinstance(result, AcsResult)
    assert result.assertion.subject == "bob@corp.example.com"


def test_full_acs_loop_role_projected_admin(
    entra_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = entra_sp
    result = accept_acs_post(
        _stub_envelope(groups=["Loop-Admins"]),
        cfg,
        bundle,
        StubSamlValidator(),
        now=_NOW,
    )
    assert result.role == "admin"


def test_full_acs_loop_role_projected_editor(
    entra_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = entra_sp
    result = accept_acs_post(
        _stub_envelope(groups=["Loop-Editors"]),
        cfg,
        bundle,
        StubSamlValidator(),
        now=_NOW,
    )
    assert result.role == "editor"


def test_full_acs_loop_default_role_no_group_match(
    entra_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = entra_sp
    result = accept_acs_post(
        _stub_envelope(groups=["Unknown-Group"]),
        cfg,
        bundle,
        StubSamlValidator(),
        now=_NOW,
    )
    assert result.role == cfg.default_role


def test_full_acs_loop_issuer_mismatch_rejected(
    entra_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = entra_sp
    with pytest.raises(SamlError, match="issuer"):
        accept_acs_post(
            _stub_envelope(issuer="https://evil.com/saml"),
            cfg,
            bundle,
            StubSamlValidator(),
            now=_NOW,
        )


def test_full_acs_loop_audience_mismatch_rejected(
    entra_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = entra_sp
    with pytest.raises(SamlError, match="audience"):
        accept_acs_post(
            _stub_envelope(audience="https://other-sp.example.com/sp"),
            cfg,
            bundle,
            StubSamlValidator(),
            now=_NOW,
        )


def test_full_acs_loop_expired_assertion_rejected(
    entra_sp: tuple[SamlSpConfig, CertificateBundle],
) -> None:
    cfg, bundle = entra_sp
    past = _NOW - timedelta(hours=2)
    with pytest.raises(SamlError, match="expired"):
        accept_acs_post(
            _stub_envelope(not_before=past - timedelta(hours=1), not_on_or_after=past),
            cfg,
            bundle,
            StubSamlValidator(),
            now=_NOW,
        )
