"""Tests for the PySAML2-backed SAML validator (S917).

Hermetic — no pysaml2 / xmlsec1 system deps required. The signature-
verification seam is mocked via :class:`_StubSignatureVerifier`; the
parsing + audience/conditions enforcement are exercised end-to-end
against hand-crafted SAML XML.

A live integration test fixture lives at
``tests/fixtures/saml/canned_okta_response.xml.b64``; the runner is
gated on ``LOOP_SAML_PYSAML2_LIVE=1`` and pysaml2 being installed.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
from loop_control_plane.saml import GroupRoleMapping, SamlError, SamlSpConfig
from loop_control_plane.saml_certs import CertificateBundle
from loop_control_plane.saml_pysaml2 import (
    PySAML2Validator,
    XmlSignatureVerifier,
    build_pysaml2_validator,
)

# --------------------------------------------------------------------------- #
# Stub signature verifier                                                     #
# --------------------------------------------------------------------------- #


@dataclass
class _StubSignatureVerifier(XmlSignatureVerifier):
    """Records each verify() call. Optionally raises to simulate bad-sig."""

    raise_on_next: BaseException | None = None
    calls: list[bytes] = field(default_factory=list)
    require_response_signature_seen: list[bool] = field(default_factory=list)

    def verify(
        self,
        xml: bytes,
        cert_bundle: CertificateBundle,
        now: datetime,
        *,
        require_response_signature: bool,
    ) -> None:
        del cert_bundle, now
        self.calls.append(xml)
        self.require_response_signature_seen.append(require_response_signature)
        if self.raise_on_next is not None:
            exc = self.raise_on_next
            self.raise_on_next = None
            raise exc


# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #


_NOW = datetime(2026, 5, 3, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def cert_bundle() -> CertificateBundle:
    return CertificateBundle(
        active_pem="-----BEGIN CERTIFICATE-----\nFAKE\n-----END CERTIFICATE-----",
    )


@pytest.fixture
def sp_config() -> SamlSpConfig:
    return SamlSpConfig(
        sp_entity_id="https://loop.example/saml/sp",
        acs_url="https://loop.example/saml/acs",
        issuer="https://idp.okta.example/saml",
        default_role="viewer",
        group_role_map=(
            GroupRoleMapping(group="loop-admins", role="admin"),
            GroupRoleMapping(group="loop-editors", role="editor"),
        ),
    )


def _build_response(
    *,
    issuer: str = "https://idp.okta.example/saml",
    subject: str = "alice@example.com",
    audience: str = "https://loop.example/saml/sp",
    not_before: str = "2026-05-03T11:55:00Z",
    not_on_or_after: str = "2026-05-03T12:30:00Z",
    groups: list[str] | None = None,
    session_index: str | None = "_session-12345",
    add_authn_statement: bool = True,
    extra_attribute: tuple[str, list[str]] | None = None,
) -> str:
    """Return a base64-encoded fake SAML Response. Only the structure
    matters; the signature seam is mocked elsewhere."""
    groups = groups or ["loop-admins"]
    attribute_xml = "\n".join(
        f"        <saml:AttributeValue>{g}</saml:AttributeValue>" for g in groups
    )
    extra_attr_xml = ""
    if extra_attribute is not None:
        name, values = extra_attribute
        value_xml = "\n".join(
            f"        <saml:AttributeValue>{v}</saml:AttributeValue>" for v in values
        )
        extra_attr_xml = f"""
      <saml:Attribute Name="{name}">
{value_xml}
      </saml:Attribute>"""
    authn_xml = (
        f"""    <saml:AuthnStatement SessionIndex="{session_index}">
      <saml:AuthnContext>
        <saml:AuthnContextClassRef>
          urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport
        </saml:AuthnContextClassRef>
      </saml:AuthnContext>
    </saml:AuthnStatement>"""
        if add_authn_statement
        else ""
    )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
                ID="_response-1" Version="2.0"
                IssueInstant="2026-05-03T12:00:00Z">
  <saml:Issuer>{issuer}</saml:Issuer>
  <saml:Assertion ID="_assertion-1" Version="2.0"
                  IssueInstant="2026-05-03T12:00:00Z">
    <saml:Issuer>{issuer}</saml:Issuer>
    <saml:Subject>
      <saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">{subject}</saml:NameID>
    </saml:Subject>
    <saml:Conditions NotBefore="{not_before}" NotOnOrAfter="{not_on_or_after}">
      <saml:AudienceRestriction>
        <saml:Audience>{audience}</saml:Audience>
      </saml:AudienceRestriction>
    </saml:Conditions>
{authn_xml}
    <saml:AttributeStatement>
      <saml:Attribute Name="groups">
{attribute_xml}
      </saml:Attribute>{extra_attr_xml}
    </saml:AttributeStatement>
  </saml:Assertion>
</samlp:Response>"""
    return base64.b64encode(xml.encode()).decode()


# --------------------------------------------------------------------------- #
# Happy path                                                                  #
# --------------------------------------------------------------------------- #


def test_valid_response_extracts_assertion(
    cert_bundle: CertificateBundle, sp_config: SamlSpConfig
) -> None:
    verifier = _StubSignatureVerifier()
    validator = PySAML2Validator(verifier=verifier)
    response = _build_response()
    assertion = validator.parse_and_validate(response, sp_config, cert_bundle, _NOW)
    assert assertion.subject == "alice@example.com"
    assert assertion.issuer == "https://idp.okta.example/saml"
    assert assertion.audience == "https://loop.example/saml/sp"
    assert assertion.attributes["groups"] == ["loop-admins"]
    assert assertion.session_index == "_session-12345"
    # Verifier saw the decoded XML and the expected signature mode.
    assert len(verifier.calls) == 1
    assert verifier.calls[0].startswith(b"<?xml")
    assert verifier.require_response_signature_seen == [True]


def test_signature_mode_passed_through_to_verifier(
    cert_bundle: CertificateBundle, sp_config: SamlSpConfig
) -> None:
    verifier = _StubSignatureVerifier()
    validator = PySAML2Validator(verifier=verifier, require_response_signature=False)
    validator.parse_and_validate(_build_response(), sp_config, cert_bundle, _NOW)
    assert verifier.require_response_signature_seen == [False]


def test_attributes_multiple_values(
    cert_bundle: CertificateBundle, sp_config: SamlSpConfig
) -> None:
    verifier = _StubSignatureVerifier()
    validator = PySAML2Validator(verifier=verifier)
    response = _build_response(groups=["loop-admins", "loop-editors", "loop-viewers"])
    assertion = validator.parse_and_validate(response, sp_config, cert_bundle, _NOW)
    assert assertion.attributes["groups"] == [
        "loop-admins",
        "loop-editors",
        "loop-viewers",
    ]


def test_extra_attribute_extracted(cert_bundle: CertificateBundle, sp_config: SamlSpConfig) -> None:
    verifier = _StubSignatureVerifier()
    validator = PySAML2Validator(verifier=verifier)
    response = _build_response(extra_attribute=("displayName", ["Alice Anderson"]))
    assertion = validator.parse_and_validate(response, sp_config, cert_bundle, _NOW)
    assert assertion.attributes["displayName"] == ["Alice Anderson"]


def test_missing_authn_statement_means_no_session_index(
    cert_bundle: CertificateBundle, sp_config: SamlSpConfig
) -> None:
    verifier = _StubSignatureVerifier()
    validator = PySAML2Validator(verifier=verifier)
    response = _build_response(add_authn_statement=False)
    assertion = validator.parse_and_validate(response, sp_config, cert_bundle, _NOW)
    assert assertion.session_index is None


# --------------------------------------------------------------------------- #
# Failure paths                                                               #
# --------------------------------------------------------------------------- #


def test_signature_verification_failure_propagates(
    cert_bundle: CertificateBundle, sp_config: SamlSpConfig
) -> None:
    verifier = _StubSignatureVerifier(raise_on_next=SamlError("bad signature"))
    validator = PySAML2Validator(verifier=verifier)
    with pytest.raises(SamlError, match="bad signature"):
        validator.parse_and_validate(_build_response(), sp_config, cert_bundle, _NOW)


def test_issuer_mismatch_rejected(cert_bundle: CertificateBundle, sp_config: SamlSpConfig) -> None:
    validator = PySAML2Validator(verifier=_StubSignatureVerifier())
    response = _build_response(issuer="https://evil.example/saml")
    with pytest.raises(SamlError, match="issuer mismatch"):
        validator.parse_and_validate(response, sp_config, cert_bundle, _NOW)


def test_audience_mismatch_rejected(
    cert_bundle: CertificateBundle, sp_config: SamlSpConfig
) -> None:
    validator = PySAML2Validator(verifier=_StubSignatureVerifier())
    response = _build_response(audience="https://otherapp.example/saml/sp")
    with pytest.raises(SamlError, match="audience mismatch"):
        validator.parse_and_validate(response, sp_config, cert_bundle, _NOW)


def test_not_yet_valid_rejected(cert_bundle: CertificateBundle, sp_config: SamlSpConfig) -> None:
    validator = PySAML2Validator(verifier=_StubSignatureVerifier())
    # NotBefore in the future, well outside clock-skew tolerance.
    response = _build_response(not_before="2026-05-03T13:00:00Z")
    with pytest.raises(SamlError, match="not yet valid"):
        validator.parse_and_validate(response, sp_config, cert_bundle, _NOW)


def test_expired_assertion_rejected(
    cert_bundle: CertificateBundle, sp_config: SamlSpConfig
) -> None:
    validator = PySAML2Validator(verifier=_StubSignatureVerifier())
    response = _build_response(not_on_or_after="2026-05-03T11:00:00Z")
    with pytest.raises(SamlError, match="expired"):
        validator.parse_and_validate(response, sp_config, cert_bundle, _NOW)


def test_clock_skew_tolerance_admits_borderline_response(
    cert_bundle: CertificateBundle, sp_config: SamlSpConfig
) -> None:
    """Default clock_skew is 2min; a NotBefore 1 minute in the future passes."""
    validator = PySAML2Validator(verifier=_StubSignatureVerifier())
    response = _build_response(not_before="2026-05-03T12:01:00Z")
    # Should not raise
    validator.parse_and_validate(response, sp_config, cert_bundle, _NOW)


def test_malformed_base64_rejected(cert_bundle: CertificateBundle, sp_config: SamlSpConfig) -> None:
    validator = PySAML2Validator(verifier=_StubSignatureVerifier())
    with pytest.raises(SamlError, match="not valid base64"):
        validator.parse_and_validate("not-base64-padding!!!", sp_config, cert_bundle, _NOW)


def test_malformed_xml_rejected(cert_bundle: CertificateBundle, sp_config: SamlSpConfig) -> None:
    validator = PySAML2Validator(verifier=_StubSignatureVerifier())
    bad = base64.b64encode(b"<not-xml").decode()
    with pytest.raises(SamlError, match="not well-formed XML"):
        validator.parse_and_validate(bad, sp_config, cert_bundle, _NOW)


def test_missing_assertion_rejected(
    cert_bundle: CertificateBundle, sp_config: SamlSpConfig
) -> None:
    validator = PySAML2Validator(verifier=_StubSignatureVerifier())
    bare = base64.b64encode(
        b'<?xml version="1.0"?><samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"/>'
    ).decode()
    with pytest.raises(SamlError, match="missing <saml:Assertion>"):
        validator.parse_and_validate(bare, sp_config, cert_bundle, _NOW)


def test_empty_cert_bundle_rejected(sp_config: SamlSpConfig) -> None:
    validator = PySAML2Validator(verifier=_StubSignatureVerifier())
    empty = CertificateBundle(active_pem="")
    with pytest.raises(SamlError, match="bundle exhausted"):
        validator.parse_and_validate(_build_response(), sp_config, empty, _NOW)


# --------------------------------------------------------------------------- #
# Time parsing edge cases                                                     #
# --------------------------------------------------------------------------- #


def test_z_suffix_normalised(cert_bundle: CertificateBundle, sp_config: SamlSpConfig) -> None:
    validator = PySAML2Validator(verifier=_StubSignatureVerifier())
    # Z and +00:00 are equivalent; both should parse.
    response = _build_response(
        not_before="2026-05-03T11:55:00Z",
        not_on_or_after="2026-05-03T12:30:00+00:00",
    )
    assertion = validator.parse_and_validate(response, sp_config, cert_bundle, _NOW)
    assert assertion.not_before.tzinfo == UTC
    assert assertion.not_on_or_after.tzinfo == UTC


def test_naive_datetime_assumed_utc(
    cert_bundle: CertificateBundle, sp_config: SamlSpConfig
) -> None:
    """Some IdPs emit naive datetimes. SAML2 spec mandates UTC; we coerce."""
    validator = PySAML2Validator(verifier=_StubSignatureVerifier())
    response = _build_response(
        not_before="2026-05-03T11:55:00",
        not_on_or_after="2026-05-03T12:30:00",
    )
    assertion = validator.parse_and_validate(response, sp_config, cert_bundle, _NOW)
    assert assertion.not_before.tzinfo == UTC


# --------------------------------------------------------------------------- #
# Factory                                                                     #
# --------------------------------------------------------------------------- #


def test_build_pysaml2_validator_with_test_verifier(
    cert_bundle: CertificateBundle, sp_config: SamlSpConfig
) -> None:
    verifier = _StubSignatureVerifier()
    validator = build_pysaml2_validator(verifier=verifier)
    validator.parse_and_validate(_build_response(), sp_config, cert_bundle, _NOW)
    assert len(verifier.calls) == 1


def test_build_pysaml2_validator_default_signature_mode_is_strict() -> None:
    validator = build_pysaml2_validator(verifier=_StubSignatureVerifier())
    assert validator.require_response_signature is True


def test_build_pysaml2_validator_can_disable_response_signature() -> None:
    validator = build_pysaml2_validator(
        verifier=_StubSignatureVerifier(),
        require_response_signature=False,
    )
    assert validator.require_response_signature is False
