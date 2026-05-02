"""Tests for SAMLAssertionParser and SP helpers — S610."""

from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from loop_control_plane.saml_sp import (
    SAMLAssertionParser,
    SAMLError,
    SAMLIdentity,
    SPConfig,
    sp_metadata_xml,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_IDP_ENTITY_ID = "https://idp.example.com/saml"
_TENANT_ID = "tenant-acme"


def _cfg(*, skip_sig: bool = True) -> SPConfig:
    return SPConfig(
        tenant_id=_TENANT_ID,
        idp_entity_id=_IDP_ENTITY_ID,
        idp_sso_url="https://idp.example.com/sso",
        idp_cert_pem_chain=[],
        unsafe_skip_signature_check=skip_sig,
    )


def _make_response(
    *,
    status_code: str = "urn:oasis:names:tc:SAML:2.0:status:Success",
    issuer: str = _IDP_ENTITY_ID,
    name_id: str = "alice@example.com",
    audience: str | None = None,
    not_on_or_after: str | None = None,
    email: str = "alice@example.com",
    given_name: str = "Alice",
    family_name: str = "Smith",
    groups: list[str] | None = None,
) -> str:
    """Build a minimal SAMLResponse XML and return it base64-encoded."""
    cfg = _cfg()
    if audience is None:
        audience = cfg.sp_entity_id

    nooa_attr = f' NotOnOrAfter="{not_on_or_after}"' if not_on_or_after else ""

    groups_xml = ""
    for g in groups or ["Loop-Admins"]:
        groups_xml += f"<saml:AttributeValue>{g}</saml:AttributeValue>"

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response
  xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
  xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
  ID="_resp1" Version="2.0" IssueInstant="2024-01-01T00:00:00Z">
  <saml:Issuer>{issuer}</saml:Issuer>
  <samlp:Status>
    <samlp:StatusCode Value="{status_code}"/>
  </samlp:Status>
  <saml:Assertion ID="_assert1" Version="2.0" IssueInstant="2024-01-01T00:00:00Z">
    <saml:Issuer>{issuer}</saml:Issuer>
    <saml:Subject>
      <saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">{name_id}</saml:NameID>
    </saml:Subject>
    <saml:Conditions{nooa_attr}>
      <saml:AudienceRestriction>
        <saml:Audience>{audience}</saml:Audience>
      </saml:AudienceRestriction>
    </saml:Conditions>
    <saml:AttributeStatement>
      <saml:Attribute Name="email">
        <saml:AttributeValue>{email}</saml:AttributeValue>
      </saml:Attribute>
      <saml:Attribute Name="firstName">
        <saml:AttributeValue>{given_name}</saml:AttributeValue>
      </saml:Attribute>
      <saml:Attribute Name="lastName">
        <saml:AttributeValue>{family_name}</saml:AttributeValue>
      </saml:Attribute>
      <saml:Attribute Name="groups">
        {groups_xml}
      </saml:Attribute>
    </saml:AttributeStatement>
  </saml:Assertion>
</samlp:Response>"""
    return base64.b64encode(xml.encode()).decode()


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


def test_parse_valid_response_returns_identity() -> None:
    parser = SAMLAssertionParser(_cfg())
    identity = parser.parse(_make_response())
    assert isinstance(identity, SAMLIdentity)
    assert identity.subject == "alice@example.com"
    assert identity.email == "alice@example.com"
    assert identity.given_name == "Alice"
    assert identity.family_name == "Smith"
    assert "Loop-Admins" in identity.groups
    assert identity.issuer == _IDP_ENTITY_ID


def test_parse_multiple_groups() -> None:
    parser = SAMLAssertionParser(_cfg())
    identity = parser.parse(_make_response(groups=["Loop-Admins", "Loop-Editors"]))
    assert set(identity.groups) == {"Loop-Admins", "Loop-Editors"}


def test_parse_session_not_on_or_after() -> None:
    future = (datetime.now(UTC) + timedelta(hours=8)).strftime("%Y-%m-%dT%H:%M:%SZ")
    parser = SAMLAssertionParser(_cfg())
    identity = parser.parse(_make_response(not_on_or_after=future))
    assert identity.session_not_on_or_after is not None
    assert identity.session_not_on_or_after > datetime.now(UTC)


# ---------------------------------------------------------------------------
# Validation failure tests
# ---------------------------------------------------------------------------


def test_rejects_non_success_status() -> None:
    resp = _make_response(status_code="urn:oasis:names:tc:SAML:2.0:status:AuthnFailed")
    parser = SAMLAssertionParser(_cfg())
    with pytest.raises(SAMLError, match="non-success status"):
        parser.parse(resp)


def test_rejects_issuer_mismatch() -> None:
    resp = _make_response(issuer="https://evil.com/saml")
    parser = SAMLAssertionParser(_cfg())
    with pytest.raises(SAMLError, match="Issuer mismatch"):
        parser.parse(resp)


def test_rejects_audience_mismatch() -> None:
    resp = _make_response(audience="https://other-sp.example.com/sp")
    parser = SAMLAssertionParser(_cfg())
    with pytest.raises(SAMLError, match="Audience mismatch"):
        parser.parse(resp)


def test_rejects_expired_assertion() -> None:
    past = "2000-01-01T00:00:00Z"
    resp = _make_response(not_on_or_after=past)
    parser = SAMLAssertionParser(_cfg())
    with pytest.raises(SAMLError, match="expired"):
        parser.parse(resp)


def test_rejects_invalid_base64() -> None:
    parser = SAMLAssertionParser(_cfg())
    with pytest.raises(SAMLError, match="not valid base64"):
        parser.parse("not!!!base64???")


def test_rejects_malformed_xml() -> None:
    bad = base64.b64encode(b"<notxml").decode()
    parser = SAMLAssertionParser(_cfg())
    with pytest.raises(SAMLError, match="malformed"):
        parser.parse(bad)


def test_requires_signature_when_not_skipped() -> None:
    cfg = _cfg(skip_sig=False)
    parser = SAMLAssertionParser(cfg)
    # Our fixture XML has no Signature element
    with pytest.raises(SAMLError, match="missing a Signature element"):
        parser.parse(_make_response())


# ---------------------------------------------------------------------------
# Cert-rotation fingerprint tests
# ---------------------------------------------------------------------------


def _dummy_cert_pem(label: str) -> str:
    """Return a fake PEM block deterministically derived from the label."""
    # 32 bytes of deterministic fake DER
    fake_der = hashlib.sha256(label.encode()).digest()
    b64 = base64.b64encode(fake_der).decode()
    return f"-----BEGIN CERTIFICATE-----\n{b64}\n-----END CERTIFICATE-----"


def test_cert_rotation_fingerprint_match() -> None:
    """Cert embedded in Signature element must match at least one chain cert."""
    cert_b = _dummy_cert_pem("cert-b")

    # Build a response with a Signature block referencing cert-a
    embedded_b64 = base64.b64encode(hashlib.sha256(b"cert-a").digest()).decode()
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response
  xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
  xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
  xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
  ID="_r" Version="2.0" IssueInstant="2024-01-01T00:00:00Z">
  <saml:Issuer>{_IDP_ENTITY_ID}</saml:Issuer>
  <ds:Signature>
    <ds:SignedInfo/>
    <ds:SignatureValue>AAAA</ds:SignatureValue>
    <ds:KeyInfo>
      <ds:X509Data>
        <ds:X509Certificate>{embedded_b64}</ds:X509Certificate>
      </ds:X509Data>
    </ds:KeyInfo>
    <ds:Reference>
      <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
      <ds:DigestValue>{embedded_b64}</ds:DigestValue>
    </ds:Reference>
  </ds:Signature>
  <samlp:Status>
    <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
  </samlp:Status>
  <saml:Assertion ID="_a" Version="2.0" IssueInstant="2024-01-01T00:00:00Z">
    <saml:Issuer>{_IDP_ENTITY_ID}</saml:Issuer>
    <saml:Subject>
      <saml:NameID>alice@example.com</saml:NameID>
    </saml:Subject>
    <saml:Conditions/>
  </saml:Assertion>
</samlp:Response>"""
    resp_b64 = base64.b64encode(xml.encode()).decode()

    # chain contains cert-a → should pass fingerprint check
    # (full RSA sig check is skipped because we have no real crypto here)
    # We get SAMLError about Audience mismatch, NOT cert fingerprint, which
    # means the fingerprint check passed.  That is what we verify.
    fake_der_a = hashlib.sha256(b"cert-a").digest()  # matches embedded_b64
    fake_pem_a = (
        "-----BEGIN CERTIFICATE-----\n"
        + base64.b64encode(fake_der_a).decode()
        + "\n-----END CERTIFICATE-----"
    )
    cfg_with_cert = SPConfig(
        tenant_id=_TENANT_ID,
        idp_entity_id=_IDP_ENTITY_ID,
        idp_sso_url="https://idp.example.com/sso",
        idp_cert_pem_chain=[fake_pem_a, cert_b],
        unsafe_skip_signature_check=False,
    )
    parser = SAMLAssertionParser(cfg_with_cert)
    # fingerprint passes → moves on to Audience check (no AudienceRestriction
    # in this trimmed XML so it silently passes) → NameID found → success
    identity = parser.parse(resp_b64)
    assert identity.subject == "alice@example.com"


def test_cert_rotation_rejects_unknown_cert() -> None:
    """A cert not in the chain must be rejected."""
    cert_b_pem = _dummy_cert_pem("cert-b")
    # Build response with cert-a embedded but chain only has cert-b
    embedded_b64 = base64.b64encode(hashlib.sha256(b"cert-a").digest()).decode()
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response
  xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
  xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
  xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
  ID="_r" Version="2.0" IssueInstant="2024-01-01T00:00:00Z">
  <saml:Issuer>{_IDP_ENTITY_ID}</saml:Issuer>
  <ds:Signature>
    <ds:SignedInfo/>
    <ds:SignatureValue>AAAA</ds:SignatureValue>
    <ds:KeyInfo>
      <ds:X509Data>
        <ds:X509Certificate>{embedded_b64}</ds:X509Certificate>
      </ds:X509Data>
    </ds:KeyInfo>
    <ds:Reference>
      <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
      <ds:DigestValue>{embedded_b64}</ds:DigestValue>
    </ds:Reference>
  </ds:Signature>
  <samlp:Status>
    <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
  </samlp:Status>
  <saml:Assertion ID="_a" Version="2.0" IssueInstant="2024-01-01T00:00:00Z">
    <saml:Issuer>{_IDP_ENTITY_ID}</saml:Issuer>
    <saml:Subject>
      <saml:NameID>alice@example.com</saml:NameID>
    </saml:Subject>
    <saml:Conditions/>
  </saml:Assertion>
</samlp:Response>"""
    resp_b64 = base64.b64encode(xml.encode()).decode()

    cfg_wrong_cert = SPConfig(
        tenant_id=_TENANT_ID,
        idp_entity_id=_IDP_ENTITY_ID,
        idp_sso_url="https://idp.example.com/sso",
        idp_cert_pem_chain=[cert_b_pem],  # cert-b, not cert-a
        unsafe_skip_signature_check=False,
    )
    parser = SAMLAssertionParser(cfg_wrong_cert)
    with pytest.raises(SAMLError, match="fingerprint mismatch"):
        parser.parse(resp_b64)


# ---------------------------------------------------------------------------
# SP metadata
# ---------------------------------------------------------------------------


def test_sp_metadata_contains_acs_url_and_entity_id() -> None:
    cfg = _cfg()
    xml = sp_metadata_xml(cfg)
    assert cfg.acs_url in xml
    assert cfg.sp_entity_id in xml
    assert "AssertionConsumerService" in xml
    assert "WantAssertionsSigned" in xml
