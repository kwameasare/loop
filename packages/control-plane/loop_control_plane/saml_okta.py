"""Okta SAML 2.0 IdP metadata parser — S612.

Parses an Okta ``EntityDescriptor`` XML document (fetched from
``https://<domain>/app/<app-id>/sso/saml/metadata``) and produces the
per-tenant :class:`~loop_control_plane.saml.SamlSpConfig` used by the
:func:`~loop_control_plane.saml.accept_acs_post` ACS handler.

Usage example::

    import pathlib
    from loop_control_plane.saml_okta import OktaMetadataParser

    xml_bytes = pathlib.Path("fixtures/okta_idp_metadata.xml").read_bytes()
    parser = OktaMetadataParser()
    idp = parser.parse(xml_bytes)
    cfg = idp.to_sp_config(
        tenant_id="ws_acme",
        default_role="member",
        group_role_map={"Loop-Admins": "admin"},
    )

The sandbox fixture at ``fixtures/okta_idp_metadata.xml`` matches the
schema this parser expects and is used by the integration test suite
(``packages/control-plane/_tests/test_okta_integration.py``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from xml.etree import ElementTree

from loop_control_plane.saml import GroupRoleMapping, SamlSpConfig
from loop_control_plane.saml_certs import CertificateBundle

_NS = {
    "md": "urn:oasis:names:tc:SAML:2.0:metadata",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}

_POST_BINDING = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
_REDIRECT_BINDING = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"

_SP_ENTITY_ID_TMPL = "https://app.loop.dev/auth/saml/sp/{tenant_id}"
_ACS_URL_TMPL = "https://app.loop.dev/auth/saml/acs/{tenant_id}"


class OktaMetadataError(ValueError):
    """Raised when the metadata XML is missing required elements."""


@dataclass(frozen=True)
class IdPMetadata:
    """Parsed IdP metadata ready to be converted into an SP config."""

    entity_id: str
    sso_url_post: str
    sso_url_redirect: str | None
    cert_pem_chain: list[str]

    def to_sp_config(
        self,
        tenant_id: str,
        *,
        default_role: str = "viewer",
        group_role_map: dict[str, str] | None = None,
        sandbox_mode: bool = False,
        groups_attribute: str = "groups",
    ) -> tuple[SamlSpConfig, CertificateBundle]:
        """Build a (:class:`SamlSpConfig`, :class:`CertificateBundle`) tuple
        for *tenant_id* from this metadata.

        Parameters
        ----------
        tenant_id:
            Loop workspace/tenant identifier (used in ACS URL and SP EntityID).
        default_role:
            Role assigned to users whose groups do not match any mapping.
        group_role_map:
            ``{okta_group_name: loop_role}`` mapping.  Keys are SAML
            ``<Attribute Name="groups">`` attribute values sent by Okta.
        sandbox_mode:
            If ``True`` the SP will accept the ``StubSamlValidator``
            hand-crafted assertions (dev / smoke-test only).

        Returns
        -------
        tuple[SamlSpConfig, CertificateBundle]
            Pass both to :func:`~loop_control_plane.saml.accept_acs_post`.
        """
        bundle = CertificateBundle(
            active_pem=self.cert_pem_chain[0],
            pending_pem=self.cert_pem_chain[1] if len(self.cert_pem_chain) > 1 else None,
        )
        mappings = tuple(
            GroupRoleMapping(group=g, role=r) for g, r in (group_role_map or {}).items()
        )
        cfg = SamlSpConfig(
            sp_entity_id=_SP_ENTITY_ID_TMPL.format(tenant_id=tenant_id),
            acs_url=_ACS_URL_TMPL.format(tenant_id=tenant_id),
            issuer=self.entity_id,
            default_role=default_role,
            group_role_map=mappings,
            sandbox_mode=sandbox_mode,
            groups_attribute=groups_attribute,
        )
        return cfg, bundle


class OktaMetadataParser:
    """Parse Okta SAML 2.0 IdP metadata XML."""

    def parse(self, xml_bytes: bytes) -> IdPMetadata:
        """Parse *xml_bytes* and return an :class:`IdPMetadata` instance.

        Raises
        ------
        OktaMetadataError
            If required elements (EntityID, SSO URL, certificate) are
            missing or malformed.
        """
        try:
            root = ElementTree.fromstring(xml_bytes)  # noqa: S314 — fixture/admin XML
        except ElementTree.ParseError as exc:
            raise OktaMetadataError(f"Metadata XML is malformed: {exc}") from exc

        entity_id = root.get("entityID", "").strip()
        if not entity_id:
            raise OktaMetadataError("EntityDescriptor is missing entityID attribute")

        idp_desc = root.find("md:IDPSSODescriptor", _NS)
        if idp_desc is None:
            raise OktaMetadataError("Metadata is missing IDPSSODescriptor element")

        sso_post = self._find_sso_url(idp_desc, _POST_BINDING)
        if not sso_post:
            raise OktaMetadataError(
                f"Metadata is missing SingleSignOnService with "
                f"HTTP-POST binding ({_POST_BINDING!r})"
            )
        sso_redirect = self._find_sso_url(idp_desc, _REDIRECT_BINDING)

        cert_pem_chain = self._extract_certs(idp_desc)
        if not cert_pem_chain:
            raise OktaMetadataError(
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
        pems: list[str] = []
        for key_desc in idp_desc.findall("md:KeyDescriptor", _NS):
            use = key_desc.get("use", "signing")
            if use not in ("signing", ""):
                continue
            cert_el = key_desc.find(".//ds:X509Certificate", _NS)
            if cert_el is not None and cert_el.text:
                body = re.sub(r"\s+", "", cert_el.text)
                pem = "-----BEGIN CERTIFICATE-----\n" + body + "\n-----END CERTIFICATE-----"
                pems.append(pem)
        return pems
