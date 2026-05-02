"""Google Workspace SAML 2.0 IdP metadata parser — S614.

Google Workspace emits standard SAML 2.0 metadata, so the XML parsing
itself is identical to :mod:`~loop_control_plane.saml_okta`. The
operational differences this module captures:

* The IdP entity ID is always ``https://accounts.google.com/o/saml2?idpid=<idpid>``.
  Studio surfaces ``<idpid>`` as the read-only "IdP ID" field.
* The SSO URL is ``https://accounts.google.com/o/saml2/idp?idpid=<idpid>``.
* Group memberships are emitted in a custom attribute. Google's admin
  console lets the admin pick the attribute name; the recommended
  default is ``groups`` (matches Okta), but many existing Workspace
  tenants use ``memberOf`` because that's what Workspace's directory
  schema uses internally. We accept either by letting the cp-api set
  :attr:`SamlSpConfig.groups_attribute` per tenant.
* Group values are **email addresses** (``loop-admins@example.com``)
  rather than display names or GUIDs.

The sandbox fixture lives at
``packages/control-plane/fixtures/google_idp_metadata.xml`` and the
integration test suite is
``packages/control-plane/_tests/test_google_integration.py``.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from loop_control_plane.saml import SamlSpConfig
from loop_control_plane.saml_certs import CertificateBundle
from loop_control_plane.saml_okta import (
    IdPMetadata,
    OktaMetadataError,
    OktaMetadataParser,
)

# Default attribute name the Studio "Connect Google Workspace" wizard
# recommends; admins may override per-tenant.
GOOGLE_DEFAULT_GROUPS_ATTRIBUTE = "groups"

# Pattern for ``https://accounts.google.com/o/saml2?idpid=<idpid>``.
_GOOGLE_ENTITY_ID_RE = re.compile(
    r"^https://accounts\.google\.com/o/saml2\?idpid=(?P<idpid>[A-Za-z0-9_\-]{6,64})$"
)

# Email-shape group values — admins must paste full addresses.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class GoogleMetadataError(OktaMetadataError):
    """Raised when the metadata is not a recognisable Google IdP doc."""


def extract_google_idp_id(idp: IdPMetadata) -> str:
    """Return the Google IdP ID from *idp*'s entity ID.

    Raises
    ------
    GoogleMetadataError
        If the entity ID does not match the
        ``https://accounts.google.com/o/saml2?idpid=<idpid>`` shape.
    """
    match = _GOOGLE_ENTITY_ID_RE.match(idp.entity_id)
    if match is None:
        raise GoogleMetadataError(
            f"entity_id {idp.entity_id!r} is not a Google Workspace issuer "
            "(expected https://accounts.google.com/o/saml2?idpid=<idpid>)"
        )
    return match.group("idpid")


class GoogleMetadataParser:
    """Parse Google Workspace SAML metadata + validate the issuer."""

    _ALLOWED_SSO_HOSTS = frozenset({"accounts.google.com"})

    def __init__(self) -> None:
        self._inner = OktaMetadataParser()

    def parse(self, xml_bytes: bytes) -> IdPMetadata:
        idp = self._inner.parse(xml_bytes)
        idpid = extract_google_idp_id(idp)  # raises if not Google
        # SSO URL must reference the same idpid — admins occasionally
        # paste mismatched docs from different SAML apps.
        sso = urlparse(idp.sso_url_post)
        if (sso.hostname or "").lower() not in self._ALLOWED_SSO_HOSTS:
            raise GoogleMetadataError(
                f"SSO URL host {sso.hostname!r} is not accounts.google.com"
            )
        sso_idpid = (parse_qs(sso.query).get("idpid") or [""])[0]
        if sso_idpid != idpid:
            raise GoogleMetadataError(
                f"entity_id idpid {idpid!r} does not match SSO URL idpid "
                f"{sso_idpid!r}; metadata appears stitched from two apps."
            )
        return idp


def build_google_sp_config(
    idp: IdPMetadata,
    *,
    tenant_id: str,
    default_role: str = "viewer",
    group_email_to_role: dict[str, str] | None = None,
    sandbox_mode: bool = False,
    groups_attribute: str = GOOGLE_DEFAULT_GROUPS_ATTRIBUTE,
) -> tuple[SamlSpConfig, CertificateBundle]:
    """Build SP config; rejects non-email group keys.

    Google Workspace emits group memberships as **email addresses**
    in the SAML attribute. Admins frequently paste display names by
    mistake — we catch that here so the failure is loud and early.
    """
    if group_email_to_role:
        for key in group_email_to_role:
            if not _EMAIL_RE.match(key):
                raise GoogleMetadataError(
                    f"Group key {key!r} is not an email address; "
                    "Google Workspace emits group emails (e.g. "
                    "'loop-admins@example.com'), not display names."
                )
    return idp.to_sp_config(
        tenant_id=tenant_id,
        default_role=default_role,
        group_role_map=group_email_to_role,
        sandbox_mode=sandbox_mode,
        groups_attribute=groups_attribute,
    )


__all__ = [
    "GOOGLE_DEFAULT_GROUPS_ATTRIBUTE",
    "GoogleMetadataError",
    "GoogleMetadataParser",
    "IdPMetadata",
    "build_google_sp_config",
    "extract_google_idp_id",
]
