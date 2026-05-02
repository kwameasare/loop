"""SAML 2.0 Service Provider primitives (S610).

This module is the **boundary** for SAML SSO in the control-plane. It
deliberately ships *without* a dependency on ``pysaml2`` /
``python3-saml`` / ``xmlsec1`` so we can unit-test the full SP flow
in plain CI without the libxml2/xmlsec1 system packages. The seam is
the :class:`SamlValidator` Protocol — production wiring (S612: Okta
integration) supplies a ``PySAML2Validator`` implementation that
parses real signed SAML responses; the rest of the control-plane
consumes :class:`SamlAssertion` and never touches XML.

Scope of this module:

* :class:`SamlAssertion` — the **post-validation** principal we hand
  off to session minting.
* :class:`SamlSpConfig` — the per-tenant SP record stored in
  ``tenant_sso.config`` (see ``engineering/SSO_SAML.md``).
* :class:`SamlValidator` — the verification Protocol.
* :class:`StubSamlValidator` — an in-process validator that consumes
  a base64'd JSON envelope. Used by tests and by the Loop
  *sandbox-tenant* mode where we accept hand-crafted assertions for
  smoke tests (see :data:`SamlSpConfig.sandbox_mode`).
* :func:`accept_acs_post` — the high-level ACS endpoint handler:
  validate, enforce audience, enforce time bounds, project
  group-role mapping, return the assertion.

The cryptographic cert-rotation primitives live in
:mod:`loop_control_plane.saml_certs` (S610) — every validator takes
a :class:`~loop_control_plane.saml_certs.CertificateBundle` so the
trust set can rotate without redeploy.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol

from loop_control_plane.saml_certs import CertificateBundle, trust_set


class SamlError(ValueError):
    """Raised when a SAML response fails validation."""


@dataclass(frozen=True, slots=True)
class SamlAssertion:
    """The validated principal extracted from a SAML response.

    All cryptographic checks (signature, digest, certificate trust)
    are completed before this object is constructed. Downstream code
    treats it as already-trusted.
    """

    subject: str
    """NameID (EmailAddress format)."""

    issuer: str
    """IdP entity id."""

    audience: str
    """SP entity id from the assertion AudienceRestriction."""

    not_before: datetime
    not_on_or_after: datetime

    attributes: dict[str, list[str]] = field(default_factory=dict)
    """Attribute statements; multi-valued (e.g. ``groups``)."""

    session_index: str | None = None
    """Used for SAML SLO; opaque to us."""


@dataclass(frozen=True, slots=True)
class GroupRoleMapping:
    group: str
    role: str  # 'owner' | 'admin' | 'editor' | 'operator' | 'viewer'


@dataclass(frozen=True, slots=True)
class SamlSpConfig:
    """Per-tenant Service Provider record."""

    sp_entity_id: str
    acs_url: str
    issuer: str
    """Expected IdP entity id (assertion.Issuer must match)."""

    default_role: str = "viewer"
    group_role_map: tuple[GroupRoleMapping, ...] = ()
    sandbox_mode: bool = False
    """When True, the StubSamlValidator is wired (no real signature
    check). For test fixtures + Loop sandbox tenants only."""

    clock_skew: timedelta = timedelta(minutes=2)
    """Tolerated drift on NotBefore / NotOnOrAfter checks."""

    groups_attribute: str = "groups"
    """SAML attribute name carrying group memberships.

    Okta and Google Workspace use the plain ``groups`` attribute; Entra ID
    uses ``http://schemas.microsoft.com/ws/2008/06/identity/claims/groups``.
    cp-api sets this per IdP type when constructing the SP config.
    """


class SamlValidator(Protocol):
    """The signature/parse boundary. Production: PySAML2; tests: stub."""

    def parse_and_validate(
        self,
        saml_response_b64: str,
        sp_config: SamlSpConfig,
        cert_bundle: CertificateBundle,
        now: datetime,
    ) -> SamlAssertion: ...


class StubSamlValidator:
    """Accepts a base64-encoded JSON envelope, no signature check.

    The envelope shape is a pure JSON serialization of the
    :class:`SamlAssertion` fields. Used by unit tests and by the
    sandbox-tenant mode (``SamlSpConfig.sandbox_mode = True``) so we
    can exercise the full ACS handler / session-minting / role
    projection pipeline in CI without the xmlsec1 system dep.
    """

    def parse_and_validate(
        self,
        saml_response_b64: str,
        sp_config: SamlSpConfig,
        cert_bundle: CertificateBundle,
        now: datetime,
    ) -> SamlAssertion:
        if not sp_config.sandbox_mode:
            raise SamlError(
                "StubSamlValidator is only valid for sandbox tenants; "
                "production tenants must use a real SamlValidator (S612)."
            )
        # Even in sandbox we still demand the cert bundle isn't empty —
        # this keeps cert-rotation discipline live in tests.
        if not trust_set(cert_bundle, now):
            raise SamlError("certificate bundle exhausted (no active or pending cert)")
        try:
            raw = base64.b64decode(saml_response_b64.encode("ascii"), validate=True)
            payload = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise SamlError(f"malformed sandbox SAML envelope: {exc}") from exc
        try:
            assertion = SamlAssertion(
                subject=payload["subject"],
                issuer=payload["issuer"],
                audience=payload["audience"],
                not_before=datetime.fromisoformat(payload["not_before"]),
                not_on_or_after=datetime.fromisoformat(payload["not_on_or_after"]),
                attributes={k: list(v) for k, v in payload.get("attributes", {}).items()},
                session_index=payload.get("session_index"),
            )
        except KeyError as exc:
            raise SamlError(f"sandbox envelope missing required field: {exc}") from exc
        return assertion


def project_role(assertion: SamlAssertion, sp_config: SamlSpConfig) -> str:
    """Project IdP groups onto a Loop workspace role.

    Highest-privilege match wins; fallback is ``sp_config.default_role``.
    """
    role_priority = ("owner", "admin", "editor", "operator", "viewer")
    groups = set(assertion.attributes.get(sp_config.groups_attribute, []))
    matched: list[str] = []
    for mapping in sp_config.group_role_map:
        if mapping.group in groups:
            matched.append(mapping.role)
    if not matched:
        return sp_config.default_role
    for role in role_priority:
        if role in matched:
            return role
    return sp_config.default_role


@dataclass(frozen=True, slots=True)
class AcsResult:
    assertion: SamlAssertion
    role: str


def accept_acs_post(
    saml_response_b64: str,
    sp_config: SamlSpConfig,
    cert_bundle: CertificateBundle,
    validator: SamlValidator,
    now: datetime | None = None,
) -> AcsResult:
    """Validate a SAML response, enforce SP invariants, project the role.

    Raises :class:`SamlError` on any failure. Caller mints a Loop
    session token from :class:`AcsResult` (out of scope for S610).
    """
    instant = now if now is not None else datetime.now(UTC)
    assertion = validator.parse_and_validate(saml_response_b64, sp_config, cert_bundle, instant)

    if assertion.issuer != sp_config.issuer:
        raise SamlError(
            f"assertion issuer {assertion.issuer!r} does not match "
            f"configured IdP {sp_config.issuer!r}"
        )
    if assertion.audience != sp_config.sp_entity_id:
        raise SamlError(
            f"assertion audience {assertion.audience!r} does not match "
            f"SP entity id {sp_config.sp_entity_id!r}"
        )
    skew = sp_config.clock_skew
    if instant + skew < assertion.not_before:
        raise SamlError("assertion is not yet valid (NotBefore in the future)")
    if instant - skew >= assertion.not_on_or_after:
        raise SamlError("assertion has expired (NotOnOrAfter passed)")

    role = project_role(assertion, sp_config)
    return AcsResult(assertion=assertion, role=role)
