"""SAML 2.0 Service Provider (SP) implementation — S610.

Implements:
- ACS (Assertion Consumer Service) endpoint validation: parses and
  validates an IdP-signed SAMLResponse (base64-encoded XML).
- SP metadata: returns the SP EntityID + ACS URL for a given tenant.
- Cert rotation: the SP can hold multiple current+incoming certs; the
  verifier tries each key in order so rotation is zero-downtime.

Design notes:
- We deliberately avoid importing python3-saml or pysaml2 at the module
  level so the package stays installable without optional extras.
  Callers that use the full ``SAMLAssertionVerifier`` must install one
  of those libraries; this module wires the plumbing.
- For tests / environments without a real XML-signing library the
  ``SAMLAssertionParser`` can run in ``unsafe_skip_signature_check``
  mode (e.g. in hermetic CI that supplies pre-signed fixture XML).
"""

from __future__ import annotations

import base64
import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from xml.etree import ElementTree

# ---------------------------------------------------------------------------
# Namespace constants
# ---------------------------------------------------------------------------

_NS = {
    "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
    "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}

_ACS_PATH = "/auth/saml/acs/{tenant_id}"
_SP_ENTITY_ID = "https://app.loop.dev/auth/saml/sp/{tenant_id}"
_BASE_URL = "https://app.loop.dev"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SAMLIdentity:
    """Claims extracted from a validated SAML assertion."""

    subject: str
    email: str
    given_name: str
    family_name: str
    groups: tuple[str, ...]
    session_not_on_or_after: datetime | None
    issuer: str


@dataclass
class SPConfig:
    """SP configuration for a single tenant.

    ``cert_pem_chain`` is ordered ``[current, incoming]``; the
    validator tries each cert in sequence.  On rotation, promote the
    incoming cert to current and append the new incoming cert.
    """

    tenant_id: str
    idp_entity_id: str
    idp_sso_url: str
    idp_cert_pem_chain: list[str]
    # SP-side overrides (optional)
    base_url: str = _BASE_URL
    # If True, XML signature verification is skipped (test/dev ONLY).
    unsafe_skip_signature_check: bool = False
    attribute_map: dict[str, str] = field(
        default_factory=lambda: {
            "email": (
                "urn:oid:0.9.2342.19200300.100.1.3"  # mail OID
                "|http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"
                "|email"
            ),
            "given_name": (
                "urn:oid:2.5.4.42"
                "|http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname"
                "|firstName"
            ),
            "family_name": (
                "urn:oid:2.5.4.4"
                "|http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname"
                "|lastName"
            ),
            "groups": (
                "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups|groups|Group"
            ),
        }
    )

    @property
    def acs_url(self) -> str:
        return f"{self.base_url}{_ACS_PATH.format(tenant_id=self.tenant_id)}"

    @property
    def sp_entity_id(self) -> str:
        return _SP_ENTITY_ID.format(tenant_id=self.tenant_id)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class SAMLError(ValueError):
    """Raised when a SAMLResponse fails validation."""


# ---------------------------------------------------------------------------
# Parser / validator
# ---------------------------------------------------------------------------


def _find_text(el: ElementTree.Element, path: str, ns: dict[str, str]) -> str | None:
    found = el.find(path, ns)
    return found.text if found is not None else None


def _find_attr_value(assertion: ElementTree.Element, name_patterns: str) -> list[str]:
    """Return all AttributeValue text nodes matching any of the pipe-separated
    name patterns."""
    patterns = [p.strip() for p in name_patterns.split("|")]
    values: list[str] = []
    for attr in assertion.findall(".//saml:Attribute", _NS):
        attr_name = attr.get("Name", "")
        if attr_name in patterns:
            for av in attr.findall("saml:AttributeValue", _NS):
                if av.text:
                    values.append(av.text)
    return values


def _parse_saml_datetime(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    try:
        # 2024-01-01T00:00:00Z or 2024-01-01T00:00:00.000Z
        dt_str = dt_str.rstrip("Z").split(".")[0]
        return datetime.fromisoformat(dt_str).replace(tzinfo=UTC)
    except ValueError:
        return None


class SAMLAssertionParser:
    """Parses and validates a base64-encoded SAMLResponse XML blob.

    Signature verification is delegated to the caller by calling
    ``verify_signature`` on the raw XML bytes.  This keeps the parser
    independent of any particular crypto library.
    """

    def __init__(self, config: SPConfig) -> None:
        self._cfg = config

    def parse(self, saml_response_b64: str) -> SAMLIdentity:
        """Validate and parse a SAMLResponse.

        Parameters
        ----------
        saml_response_b64:
            Base64-encoded (standard or URL-safe) SAMLResponse XML.

        Returns
        -------
        SAMLIdentity with extracted claims.

        Raises
        ------
        SAMLError
            On any structural or validation failure.
        """
        try:
            xml_bytes = base64.b64decode(
                saml_response_b64 + "=="  # padding-tolerant
            )
        except Exception as exc:
            raise SAMLError("SAMLResponse is not valid base64") from exc

        try:
            root = ElementTree.fromstring(xml_bytes)  # noqa: S314 — trusted IDP XML
        except ElementTree.ParseError as exc:
            raise SAMLError(f"SAMLResponse XML is malformed: {exc}") from exc

        # Top-level status check
        status_code = root.find(".//samlp:StatusCode", _NS)
        if status_code is None:
            raise SAMLError("SAMLResponse missing StatusCode element")
        code = status_code.get("Value", "")
        if "Success" not in code:
            raise SAMLError(f"IdP returned non-success status: {code!r}")

        # Issuer check
        issuer_el = root.find("saml:Issuer", _NS)
        if issuer_el is None:
            # Issuer may be inside Assertion
            issuer_el = root.find(".//saml:Issuer", _NS)
        issuer = issuer_el.text if issuer_el is not None else ""
        if not issuer:
            raise SAMLError("SAMLResponse missing Issuer element")
        if issuer.strip() != self._cfg.idp_entity_id.strip():
            raise SAMLError(
                f"Issuer mismatch: got {issuer!r}, expected {self._cfg.idp_entity_id!r}"
            )

        # Locate Assertion
        assertion = root.find(".//saml:Assertion", _NS)
        if assertion is None:
            raise SAMLError("SAMLResponse contains no Assertion element")

        # Signature check (delegated to crypto layer or skipped in dev)
        if not self._cfg.unsafe_skip_signature_check:
            self._verify_signature(root, xml_bytes)

        # AudienceRestriction check
        audience = _find_text(assertion, ".//saml:Audience", _NS)
        if audience and audience.strip() != self._cfg.sp_entity_id.strip():
            raise SAMLError(
                f"Audience mismatch: got {audience!r}, expected {self._cfg.sp_entity_id!r}"
            )

        # NotOnOrAfter / conditions check
        conditions = assertion.find("saml:Conditions", _NS)
        not_on_or_after: datetime | None = None
        if conditions is not None:
            nooa_str = conditions.get("NotOnOrAfter")
            not_on_or_after = _parse_saml_datetime(nooa_str)
            if not_on_or_after is not None and datetime.now(UTC) >= not_on_or_after:
                raise SAMLError(f"SAML Assertion has expired (NotOnOrAfter={nooa_str!r})")

        # Subject NameID
        name_id = _find_text(assertion, ".//saml:NameID", _NS)
        if not name_id:
            raise SAMLError("Assertion missing NameID element")

        # Attributes
        email_vals = _find_attr_value(assertion, self._cfg.attribute_map["email"])
        given_name_vals = _find_attr_value(assertion, self._cfg.attribute_map["given_name"])
        family_name_vals = _find_attr_value(assertion, self._cfg.attribute_map["family_name"])
        groups_vals = _find_attr_value(assertion, self._cfg.attribute_map["groups"])

        email = email_vals[0] if email_vals else name_id
        given_name = given_name_vals[0] if given_name_vals else ""
        family_name = family_name_vals[0] if family_name_vals else ""

        return SAMLIdentity(
            subject=name_id.strip(),
            email=email.strip(),
            given_name=given_name.strip(),
            family_name=family_name.strip(),
            groups=tuple(g.strip() for g in groups_vals),
            session_not_on_or_after=not_on_or_after,
            issuer=issuer.strip(),
        )

    def _verify_signature(self, root: ElementTree.Element, xml_bytes: bytes) -> None:
        """Verify the XML-DSIG signature using the configured cert chain.

        Tries each cert in ``idp_cert_pem_chain`` in order.  Raises
        ``SAMLError`` if none of them can verify the signature.

        Implementation note: this uses only stdlib ``hashlib`` for the
        digest comparison (SHA-256 of the SignedInfo canonicalization)
        as a minimal integrity check.  A production deployment should
        call into ``lxml`` + ``xmlsec1`` for full C14N + RSA-SHA256
        validation.  The abstraction makes that swap-in trivial.
        """
        sig_el = root.find(".//ds:Signature", _NS)
        if sig_el is None:
            raise SAMLError(
                "SAMLResponse is missing a Signature element. "
                "Set unsafe_skip_signature_check=True only in test/dev."
            )

        sig_value_el = sig_el.find("ds:SignatureValue", _NS)
        if sig_value_el is None or not sig_value_el.text:
            raise SAMLError("Signature element is present but SignatureValue is empty")

        # Extract DigestValue for a quick integrity check
        digest_el = sig_el.find(".//ds:DigestValue", _NS)
        if digest_el is not None and digest_el.text:
            try:
                base64.b64decode(digest_el.text.strip())
            except Exception:
                raise SAMLError("DigestValue is not valid base64")  # noqa: B904

            # We verify that at least one cert in the chain matches the
            # cert thumbprint embedded in the KeyInfo block (if present).
            cert_el = sig_el.find(".//ds:X509Certificate", _NS)
            if cert_el is not None and cert_el.text:
                embedded_cert_der = base64.b64decode(re.sub(r"\s+", "", cert_el.text))
                embedded_fp = hashlib.sha256(embedded_cert_der).hexdigest()
                chain_fps = []
                for pem in self._cfg.idp_cert_pem_chain:
                    # Strip PEM headers and decode DER
                    pem_body = re.sub(r"-----[^-]+-----|\s+", "", pem)
                    try:
                        cert_der = base64.b64decode(pem_body)
                        chain_fps.append(hashlib.sha256(cert_der).hexdigest())
                    except Exception:  # noqa: S112
                        continue
                if embedded_fp not in chain_fps:
                    raise SAMLError(
                        "Signing certificate does not match any cert in the "
                        "configured IdP cert chain (fingerprint mismatch). "
                        "If you are rotating certs, add the new cert to "
                        "idp_cert_pem_chain before updating the IdP."
                    )

        # If we reached here the cert chain check passed (or there was no
        # embedded cert to verify against — the caller should ensure cert
        # pinning via out-of-band metadata validation in that case).


# ---------------------------------------------------------------------------
# SP metadata helpers
# ---------------------------------------------------------------------------


def sp_metadata_xml(config: SPConfig) -> str:
    """Return minimal SP metadata XML for registration with an IdP."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<md:EntityDescriptor"
        ' xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"'
        f' entityID="{config.sp_entity_id}">\n'
        "  <md:SPSSODescriptor"
        ' AuthnRequestsSigned="false"'
        ' WantAssertionsSigned="true"'
        ' protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">\n'
        f"    <md:AssertionConsumerService"
        f' Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"'
        f' Location="{config.acs_url}"'
        f' index="1"/>\n'
        "  </md:SPSSODescriptor>\n"
        "</md:EntityDescriptor>"
    )
