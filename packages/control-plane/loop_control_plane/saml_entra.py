"""Microsoft Entra ID (Azure AD) SAML 2.0 metadata parser — S613.

Entra ID emits standard SAML 2.0 metadata, so the XML parsing logic
itself is identical to :mod:`~loop_control_plane.saml_okta`.  The
differences this module captures are operational:

* The IdP entity ID is always ``https://sts.windows.net/{tenant}/``
  (where *tenant* is an Entra tenant GUID).  We expose
  :func:`extract_entra_tenant_id` so the cp-api layer can stamp the
  Entra-side tenant on the resulting :class:`SamlSpConfig` for audit.
* Group claims are emitted under the WS-Federation URI
  ``http://schemas.microsoft.com/ws/2008/06/identity/claims/groups``
  rather than the plain ``groups`` attribute Okta uses, and the
  values are **GUIDs** not display names — so group→role mapping
  must be configured against the Entra group's *Object ID*.
* When the Entra app registration enables "send group memberships
  as filter", the SSO URL becomes
  ``https://login.microsoftonline.com/{tenant}/saml2`` (already
  encoded in the metadata XML — we just surface it).

The sandbox fixture lives at
``packages/control-plane/fixtures/entra_idp_metadata.xml`` and the
integration test suite is
``packages/control-plane/_tests/test_entra_integration.py``.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from loop_control_plane.saml_certs import CertificateBundle
from loop_control_plane.saml_okta import (
    IdPMetadata,
    OktaMetadataError,
    OktaMetadataParser,
)

# Entra emits group memberships under the WS-Fed claim URI.
# Studio's group-role mapping UI must show this attribute name when
# the IdP type is "entra" so admins know which claim to inspect.
ENTRA_GROUPS_CLAIM = (
    "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups"
)

# Pattern for ``https://sts.windows.net/{guid}/`` — Entra's IdP entity ID.
# Trailing slash is optional per Microsoft's spec but always present in
# real metadata; we accept both for forgiveness.
_ENTRA_TENANT_RE = re.compile(
    r"^https://sts\.windows\.net/(?P<tenant>[0-9a-fA-F\-]{36})/?$"
)


class EntraMetadataError(OktaMetadataError):
    """Raised when the metadata is not a recognisable Entra IdP doc."""


def extract_entra_tenant_id(idp: IdPMetadata) -> str:
    """Return the Entra tenant GUID from *idp*'s entity ID.

    Raises
    ------
    EntraMetadataError
        If the entity ID does not match the
        ``https://sts.windows.net/<guid>/`` shape.
    """
    match = _ENTRA_TENANT_RE.match(idp.entity_id)
    if match is None:
        raise EntraMetadataError(
            f"entity_id {idp.entity_id!r} is not an Entra ID issuer "
            "(expected https://sts.windows.net/<tenant-guid>/)"
        )
    return match.group("tenant")


class EntraMetadataParser:
    """Parse Microsoft Entra ID SAML metadata and validate the issuer.

    Wraps :class:`OktaMetadataParser` (the parsing surface is identical
    OASIS SAML 2.0 metadata) and adds Entra-specific validation:

    * Entity ID must be ``https://sts.windows.net/<guid>/``.
    * SSO URL must be on ``login.microsoftonline.com`` (catches admins
      who pasted the wrong app's metadata).
    """

    _ALLOWED_SSO_HOSTS = frozenset(
        {
            "login.microsoftonline.com",
            "login.microsoftonline.us",  # GCC High
            "login.partner.microsoftonline.cn",  # 21Vianet
        }
    )

    def __init__(self) -> None:
        self._inner = OktaMetadataParser()

    def parse(self, xml_bytes: bytes) -> IdPMetadata:
        idp = self._inner.parse(xml_bytes)
        # Validate Entra-specific shape before the caller wires it up.
        extract_entra_tenant_id(idp)  # raises EntraMetadataError
        host = urlparse(idp.sso_url_post).hostname or ""
        if host.lower() not in self._ALLOWED_SSO_HOSTS:
            raise EntraMetadataError(
                f"SSO URL host {host!r} is not a recognised Entra "
                "endpoint; metadata may be from a different IdP."
            )
        return idp


def build_entra_sp_config(
    idp: IdPMetadata,
    *,
    tenant_id: str,
    default_role: str = "viewer",
    group_object_id_to_role: dict[str, str] | None = None,
    sandbox_mode: bool = False,
) -> tuple["SamlSpConfig", CertificateBundle]:  # type: ignore[name-defined]
    """Convenience wrapper — Entra group keys are *Object IDs* (GUIDs).

    Studio's UI passes a dict whose keys are the group GUIDs (because
    that's what Entra puts in the SAML attribute) rather than display
    names.  We forward to :meth:`IdPMetadata.to_sp_config` which is
    naive about key semantics, but having this entry point makes
    intent explicit and catches the common admin mistake of pasting
    a display name.
    """
    if group_object_id_to_role:
        for key in group_object_id_to_role:
            if not _ENTRA_GROUP_ID_RE.match(key):
                raise EntraMetadataError(
                    f"Group key {key!r} is not a GUID; Entra emits "
                    "group Object IDs in the groups claim, not display "
                    "names. Use the Object ID from Azure Portal."
                )
    return idp.to_sp_config(
        tenant_id=tenant_id,
        default_role=default_role,
        group_role_map=group_object_id_to_role,
        sandbox_mode=sandbox_mode,
        groups_attribute=ENTRA_GROUPS_CLAIM,
    )


_ENTRA_GROUP_ID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


# Re-export for convenience: callers can do
# ``from loop_control_plane.saml_entra import IdPMetadata`` without
# reaching into the Okta module.
__all__ = [
    "ENTRA_GROUPS_CLAIM",
    "EntraMetadataError",
    "EntraMetadataParser",
    "IdPMetadata",
    "build_entra_sp_config",
    "extract_entra_tenant_id",
]


# Lazy import to avoid a hard cycle for the type-only use above.
from loop_control_plane.saml import SamlSpConfig  # noqa: E402  (kept at bottom for cycle)
