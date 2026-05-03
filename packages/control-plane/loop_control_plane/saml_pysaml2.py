# ruff: noqa: S314  -- xmlsec1 verifies the signature *before* this module
# parses the XML; ElementTree is appropriate for the post-verify shape walk.
"""PySAML2-backed SAML response validator (S917).

Real signature-verifying implementation of the
:class:`~loop_control_plane.saml.SamlValidator` Protocol. Replaces
:class:`~loop_control_plane.saml.StubSamlValidator` in production paths
when ``LOOP_SAML_USE_PYSAML2=1`` is set.

Why this exists
===============

The original SAML SP shipped a ``StubSamlValidator`` that accepts a
base64 JSON envelope, no signature check. That's fine for sandbox
tenants and unit tests but cannot interop with Okta / Entra ID /
Google Workspace because none of them sign assertions in JSON. S917
wires the real path: pysaml2 + xmlsec1 verify a real XML SAML
response, then we parse the assertion ourselves.

Architecture
============

The validator splits the work into two seams:

1. **Signature verification** — the bit that needs pysaml2 + xmlsec1
   system packages. We expose this as the
   :class:`XmlSignatureVerifier` Protocol so tests can inject a stub
   that records the call without depending on the heavy native libs.

2. **Response parsing + audience/conditions enforcement** — pure
   Python on top of stdlib ``xml.etree.ElementTree``. This is what
   converts the verified XML into a :class:`SamlAssertion`.

Production wires :class:`_PySAML2SignatureVerifier`, which lazy-imports
``pysaml2.sigver`` and verifies the document signature against every
active certificate in the
:class:`~loop_control_plane.saml_certs.CertificateBundle`.

Tests use :class:`_StubSignatureVerifier` from
``packages/control-plane/_tests/test_saml_pysaml2.py`` to exercise the
parsing layer with hand-crafted SAML XML.

Optional dependency
===================

``pysaml2`` is an *optional* extra (``loop-control-plane[saml]``)
because xmlsec1 carries native-library dependencies (libxml2, libxslt,
xmlsec1 itself). Customers running on the StubSamlValidator (sandbox
tenants only) shouldn't have to install the system packages.

If ``LOOP_SAML_USE_PYSAML2=1`` is set but ``pysaml2`` isn't installed,
:func:`build_pysaml2_validator` raises :class:`SamlError` with a clear
install hint.

ENV
===

* ``LOOP_SAML_USE_PYSAML2`` — set to ``1`` to wire this validator into
  the cp-api app. Default ``0`` (StubSamlValidator).
* ``LOOP_SAML_REQUIRE_RESPONSE_SIGNATURE`` — when ``1`` (default), the
  whole ``<samlp:Response>`` envelope must be signed. When ``0``, only
  the inner ``<saml:Assertion>`` must be signed (per Okta's default
  config). Both modes still require *some* signature.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from xml.etree import ElementTree as ET

from .saml import (
    SamlAssertion,
    SamlError,
    SamlSpConfig,
    SamlValidator,
)
from .saml_certs import CertificateBundle, trust_set

__all__ = [
    "PySAML2Validator",
    "XmlSignatureVerifier",
    "build_pysaml2_validator",
]


# SAML namespaces — used everywhere we touch SAML XML.
_NS = {
    "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
    "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}


# --------------------------------------------------------------------------- #
# Signature-verification seam                                                 #
# --------------------------------------------------------------------------- #


class XmlSignatureVerifier(Protocol):
    """The signature-check boundary.

    Production: :class:`_PySAML2SignatureVerifier` wraps
    ``pysaml2.sigver``. Tests inject a stub.

    Implementations must raise :class:`SamlError` on any failure
    (bad signature, expired cert, untrusted issuer, malformed XML).
    """

    def verify(
        self,
        xml: bytes,
        cert_bundle: CertificateBundle,
        now: datetime,
        *,
        require_response_signature: bool,
    ) -> None: ...


# --------------------------------------------------------------------------- #
# Production validator                                                        #
# --------------------------------------------------------------------------- #


@dataclass
class PySAML2Validator:
    """Real SAML validator: verifies signature, then extracts assertion.

    The :data:`require_response_signature` flag follows
    ``LOOP_SAML_REQUIRE_RESPONSE_SIGNATURE``. When ``True`` (default),
    the ``<samlp:Response>`` envelope itself must be signed. When
    ``False``, only the inner ``<saml:Assertion>`` must be signed
    (Okta's default; Entra also defaults this way for SP-initiated
    flows).
    """

    verifier: XmlSignatureVerifier
    require_response_signature: bool = True

    def parse_and_validate(
        self,
        saml_response_b64: str,
        sp_config: SamlSpConfig,
        cert_bundle: CertificateBundle,
        now: datetime,
    ) -> SamlAssertion:
        # 1. Decode + cert-bundle freshness
        if not trust_set(cert_bundle, now):
            raise SamlError("certificate bundle exhausted (no active or pending cert)")
        xml = self._decode(saml_response_b64)

        # 2. Verify signature (delegates to pysaml2.sigver in prod)
        self.verifier.verify(
            xml,
            cert_bundle,
            now,
            require_response_signature=self.require_response_signature,
        )

        # 3. Parse + enforce audience / conditions / time bounds
        return self._extract_assertion(xml, sp_config, now)

    # ---- internal --------------------------------------------------------

    @staticmethod
    def _decode(saml_response_b64: str) -> bytes:
        try:
            return base64.b64decode(saml_response_b64.encode(), validate=True)
        except (ValueError, TypeError) as exc:
            raise SamlError(f"saml response is not valid base64: {exc}") from exc

    def _extract_assertion(
        self,
        xml: bytes,
        sp_config: SamlSpConfig,
        now: datetime,
    ) -> SamlAssertion:
        try:
            root = ET.fromstring(xml)
        except ET.ParseError as exc:
            raise SamlError(f"saml response is not well-formed XML: {exc}") from exc

        # Some IdPs (Entra) wrap Assertion under Response; some
        # (Okta with EncryptedAssertion off) put it as the only
        # top-level element. We accept either.
        assertion = root.find(".//saml:Assertion", _NS)
        if assertion is None:
            raise SamlError("saml response missing <saml:Assertion>")

        issuer_el = assertion.find("saml:Issuer", _NS)
        if issuer_el is None or not (issuer_el.text or "").strip():
            raise SamlError("saml assertion missing <saml:Issuer>")
        issuer = issuer_el.text.strip()
        if issuer != sp_config.issuer:
            raise SamlError(f"saml issuer mismatch: expected {sp_config.issuer!r}, got {issuer!r}")

        subject_el = assertion.find("saml:Subject/saml:NameID", _NS)
        if subject_el is None or not (subject_el.text or "").strip():
            raise SamlError("saml assertion missing <saml:Subject><saml:NameID>")
        subject = subject_el.text.strip()

        conditions = assertion.find("saml:Conditions", _NS)
        if conditions is None:
            raise SamlError("saml assertion missing <saml:Conditions>")

        not_before = self._parse_time(
            conditions.attrib.get("NotBefore"),
            field_name="Conditions.NotBefore",
        )
        not_on_or_after = self._parse_time(
            conditions.attrib.get("NotOnOrAfter"),
            field_name="Conditions.NotOnOrAfter",
        )

        # Apply clock skew tolerance from sp_config.
        skew = sp_config.clock_skew
        if now + skew < not_before:
            raise SamlError(
                f"saml assertion not yet valid: now={now.isoformat()} < "
                f"NotBefore={not_before.isoformat()} (skew={skew})"
            )
        if now - skew >= not_on_or_after:
            raise SamlError(
                f"saml assertion expired: now={now.isoformat()} >= "
                f"NotOnOrAfter={not_on_or_after.isoformat()} (skew={skew})"
            )

        # Audience MUST contain the SP entity ID (per OASIS SAML2 §2.5.1.4).
        audiences = [
            (a.text or "").strip()
            for a in conditions.findall("saml:AudienceRestriction/saml:Audience", _NS)
        ]
        if sp_config.sp_entity_id not in audiences:
            raise SamlError(
                f"saml audience mismatch: SP={sp_config.sp_entity_id!r} not in "
                f"AudienceRestriction={audiences}"
            )

        attributes: dict[str, list[str]] = {}
        for attr in assertion.findall("saml:AttributeStatement/saml:Attribute", _NS):
            name = attr.attrib.get("Name") or attr.attrib.get("FriendlyName")
            if not name:
                continue
            values = [
                (v.text or "").strip()
                for v in attr.findall("saml:AttributeValue", _NS)
                if v.text is not None
            ]
            attributes.setdefault(name, []).extend(values)

        session_index: str | None = None
        for an_stmt in assertion.findall("saml:AuthnStatement", _NS):
            si = an_stmt.attrib.get("SessionIndex")
            if si:
                session_index = si
                break

        return SamlAssertion(
            subject=subject,
            issuer=issuer,
            audience=sp_config.sp_entity_id,
            not_before=not_before,
            not_on_or_after=not_on_or_after,
            attributes=attributes,
            session_index=session_index,
        )

    @staticmethod
    def _parse_time(value: str | None, *, field_name: str) -> datetime:
        if not value:
            raise SamlError(f"saml assertion {field_name} missing")
        # SAML times use ISO 8601 UTC. Python <3.11's fromisoformat doesn't
        # accept the trailing 'Z'; we normalise here.
        normalised = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalised)
        except ValueError as exc:
            raise SamlError(f"saml assertion {field_name} is not ISO 8601: {value!r}") from exc
        # Force UTC. SAML2 spec requires UTC; some IdPs send tzinfo=None.
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)


# --------------------------------------------------------------------------- #
# Lazy pysaml2 wiring                                                         #
# --------------------------------------------------------------------------- #


class _PySAML2SignatureVerifier:
    """Wraps ``pysaml2.sigver`` for real XML signature verification.

    Each call constructs a temporary ``SecurityContext`` from the
    active certificates in :class:`CertificateBundle`. We do this per
    call because the bundle can rotate; pysaml2's ``SecurityContext``
    isn't designed for hot-reload.
    """

    def verify(
        self,
        xml: bytes,
        cert_bundle: CertificateBundle,
        now: datetime,
        *,
        require_response_signature: bool,
    ) -> None:
        try:
            from saml2.sigver import (  # type: ignore[import-untyped]
                SecurityContext,
                SignatureError,
            )
        except ImportError as exc:
            raise SamlError(
                "PySAML2Validator requires pysaml2 + xmlsec1 system package. "
                "Install with: uv pip install -e 'packages/control-plane[saml]' "
                "and `apt install xmlsec1` (Linux) or `brew install libxmlsec1` (macOS)."
            ) from exc

        trusted_pems = trust_set(cert_bundle, now)
        if not trusted_pems:
            raise SamlError("certificate bundle exhausted (no active certs)")

        # Build a SecurityContext seeded with each trusted cert PEM. pysaml2
        # walks the chain and accepts the response if any one cert verifies
        # the signature. ``trust_set`` returns PEM strings directly.
        ctx = SecurityContext(
            metadata=None,
            cert_file=None,
            key_file=None,
            cert_handler=None,
        )
        ctx.cert_chain = list(trusted_pems)

        try:
            ctx.correctly_signed_response(
                xml.decode(),
                require_response_signature=require_response_signature,
            )
        except SignatureError as exc:
            raise SamlError(f"saml signature verification failed: {exc}") from exc
        except Exception as exc:
            raise SamlError(f"saml signature verification error: {exc}") from exc


def build_pysaml2_validator(
    *,
    require_response_signature: bool = True,
    verifier: XmlSignatureVerifier | None = None,
) -> PySAML2Validator:
    """Construct a production-wired :class:`PySAML2Validator`.

    Imports pysaml2 lazily; raises :class:`SamlError` with a clear
    install hint if pysaml2 isn't installed.

    Tests can pass a custom ``verifier`` to bypass pysaml2 entirely.
    """
    if verifier is not None:
        return PySAML2Validator(
            verifier=verifier,
            require_response_signature=require_response_signature,
        )
    return PySAML2Validator(
        verifier=_PySAML2SignatureVerifier(),
        require_response_signature=require_response_signature,
    )


# Make sure PySAML2Validator satisfies the SamlValidator protocol at type-check
# time. (Runtime check is implicit via duck typing.)
_: SamlValidator = PySAML2Validator(verifier=_PySAML2SignatureVerifier())
del _
