"""Microsoft Entra ID (Azure AD) SAML 2.0 IdP metadata parser — S613.

Parses an Entra ID ``EntityDescriptor`` XML document and produces the
per-tenant :class:`~loop_control_plane.saml.SamlSpConfig` used by the
:func:`~loop_control_plane.saml.accept_acs_post` ACS handler.

Entra-specific details
-----------------------
* The federation metadata URL is:
  ``https://login.microsoftonline.com/<tenant-id>/federationmetadata/2007-06/federationmetadata.xml``
  or available from the Enterprise App → Single sign-on → SAML Certificates page.
* ``entityID`` uses the form ``https://sts.windows.net/<tenant-id>/``.
* The SSO URL (HTTP-POST binding) is:
  ``https://login.microsoftonline.com/<tenant-id>/saml2``.
* Entra uses the default SAML metadata namespace (no ``md:`` prefix in the
  raw XML); :mod:`xml.etree.ElementTree` resolves this identically to the
  ``md:``-prefixed variant used by Okta.
* Entra metadata often omits the ``use`` attribute on ``<KeyDescriptor>``
  (defaulting to both signing and encryption).  :class:`EntraMetadataParser`
  includes all key descriptors that are absent a ``use`` attribute **or**
  are explicitly ``use="signing"``.

Usage example::

    import pathlib
    from loop_control_plane.saml_entra import EntraMetadataParser

    xml_bytes = pathlib.Path("fixtures/entra_idp_metadata.xml").read_bytes()
    parser = EntraMetadataParser()
    idp = parser.parse(xml_bytes)
    cfg, bundle = idp.to_sp_config(
        tenant_id="ws_acme",
        default_role="viewer",
        group_role_map={"Loop-Admins": "admin"},
    )

The sandbox fixture at ``fixtures/entra_idp_metadata.xml`` matches the
schema this parser expects and is used by the integration test suite
(``packages/control-plane/_tests/test_entra_integration.py``).

Shared data model
-----------------
:class:`~loop_control_plane.saml_okta.IdPMetadata` is re-exported here for
consumer convenience — the parsed result is the same record whether the
upstream IdP is Okta or Entra ID.
"""

from __future__ import annotations

import re
from xml.etree import ElementTree

# IdPMetadata and the SP URL templates are shared with the Okta parser.
# Re-exporting IdPMetadata avoids duplicating the dataclass.
from loop_control_plane.saml_okta import (
    _POST_BINDING,
    _REDIRECT_BINDING,
    IdPMetadata,
)

_NS = {
    "md": "urn:oasis:names:tc:SAML:2.0:metadata",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}

__all__ = ["EntraMetadataError", "EntraMetadataParser", "IdPMetadata"]


class EntraMetadataError(ValueError):
    """Raised when the Entra ID metadata XML is missing required elements."""


class EntraMetadataParser:
    """Parse Microsoft Entra ID SAML 2.0 IdP metadata XML.

    Handles both the default-namespace (no prefix) and ``md:``-prefixed
    variants of SAML metadata — ElementTree normalises them identically.
    """

    def parse(self, xml_bytes: bytes) -> IdPMetadata:
        """Parse *xml_bytes* and return an :class:`IdPMetadata` instance.

        Raises
        ------
        EntraMetadataError
            If required elements (EntityID, SSO URL, certificate) are
            missing or malformed.
        """
        try:
            root = ElementTree.fromstring(xml_bytes)  # noqa: S314 — fixture/admin XML
        except ElementTree.ParseError as exc:
            raise EntraMetadataError(f"Metadata XML is malformed: {exc}") from exc

        entity_id = root.get("entityID", "").strip()
        if not entity_id:
            raise EntraMetadataError("EntityDescriptor is missing entityID attribute")

        idp_desc = root.find("md:IDPSSODescriptor", _NS)
        if idp_desc is None:
            raise EntraMetadataError("Metadata is missing IDPSSODescriptor element")

        sso_post = self._find_sso_url(idp_desc, _POST_BINDING)
        if not sso_post:
            raise EntraMetadataError(
                f"Metadata is missing SingleSignOnService with "
                f"HTTP-POST binding ({_POST_BINDING!r})"
            )
        sso_redirect = self._find_sso_url(idp_desc, _REDIRECT_BINDING)

        cert_pem_chain = self._extract_certs(idp_desc)
        if not cert_pem_chain:
            raise EntraMetadataError(
                "Metadata contains no X509Certificate in a signing KeyDescriptor"
            )

        return IdPMetadata(
            entity_id=entity_id,
            sso_url_post=sso_post,
            sso_url_redirect=sso_redirect,
            cert_pem_chain=cert_pem_chain,
        )

    @staticmethod
    def _find_sso_url(idp_desc: ElementTree.Element, binding: str) -> str | None:
        for sso in idp_desc.findall("md:SingleSignOnService", _NS):
            if sso.get("Binding") == binding:
                return sso.get("Location", "").strip() or None
        return None

    @staticmethod
    def _extract_certs(idp_desc: ElementTree.Element) -> list[str]:
        """Extract PEM-formatted certs from all signing KeyDescriptors.

        Entra often omits ``use`` (meaning both signing + encryption); we
        include those alongside explicit ``use="signing"`` entries.
        """
        pems: list[str] = []
        for key_desc in idp_desc.findall("md:KeyDescriptor", _NS):
            use = key_desc.get("use", "signing")
            # Accept absent ``use`` (Entra default) or explicit "signing".
            if use not in ("signing", ""):
                continue
            cert_el = key_desc.find(".//ds:X509Certificate", _NS)
            if cert_el is not None and cert_el.text:
                body = re.sub(r"\s+", "", cert_el.text)
                pem = "-----BEGIN CERTIFICATE-----\n" + body + "\n-----END CERTIFICATE-----"
                pems.append(pem)
        return pems
