"""Google Workspace SAML 2.0 IdP metadata parser — S614.

Parses a Google Workspace ``EntityDescriptor`` XML document and produces
the per-tenant :class:`~loop_control_plane.saml.SamlSpConfig` used by the
:func:`~loop_control_plane.saml.accept_acs_post` ACS handler.

Google Workspace-specific details
-----------------------------------
* The metadata URL is available from the Admin console:
  ``Admin console -> Apps -> Web and mobile apps -> <your SAML app>
  -> Download IdP metadata``
* ``entityID`` typically has the form:
  ``https://accounts.google.com/o/saml2?idpid=<App ID>``
* SSO URL (HTTP-POST):
  ``https://accounts.google.com/o/saml2/idp?idpid=<App ID>``
* Google auto-rotates SAML signing certificates; always re-download and
  re-upload the metadata after a rotation event.
* The XML uses the ``md:``-prefixed namespace (same as Okta), so
  :class:`GoogleMetadataParser` delegates directly to
  :class:`~loop_control_plane.saml_okta.OktaMetadataParser`.

Usage example::

    import pathlib
    from loop_control_plane.saml_google import GoogleMetadataParser

    xml_bytes = pathlib.Path("fixtures/google_idp_metadata.xml").read_bytes()
    parser = GoogleMetadataParser()
    idp = parser.parse(xml_bytes)
    cfg, bundle = idp.to_sp_config(
        tenant_id="ws_acme",
        default_role="viewer",
        group_role_map={"loop-admins@corp.example.com": "admin"},
    )

The sandbox fixture at ``fixtures/google_idp_metadata.xml`` matches the
schema this parser expects and is used by the integration test suite
(``packages/control-plane/_tests/test_google_integration.py``).

Shared data model
-----------------
:class:`~loop_control_plane.saml_okta.IdPMetadata` is re-exported here for
consumer convenience.
"""

from __future__ import annotations

from loop_control_plane.saml_okta import IdPMetadata, OktaMetadataParser

__all__ = ["GoogleMetadataError", "GoogleMetadataParser", "IdPMetadata"]


class GoogleMetadataError(ValueError):
    """Raised when the Google Workspace metadata XML is missing required elements."""


class GoogleMetadataParser:
    """Parse Google Workspace SAML 2.0 IdP metadata XML.

    Google Workspace produces ``md:``-prefixed SAML metadata that is
    structurally identical to Okta metadata.  This parser wraps
    :class:`~loop_control_plane.saml_okta.OktaMetadataParser` and
    re-raises its errors as :class:`GoogleMetadataError` so callers can
    distinguish IdP-specific failures in error handling.
    """

    def __init__(self) -> None:
        self._delegate = OktaMetadataParser()

    def parse(self, xml_bytes: bytes) -> IdPMetadata:
        """Parse *xml_bytes* and return an :class:`IdPMetadata` instance.

        Raises
        ------
        GoogleMetadataError
            If required elements (EntityID, SSO URL, certificate) are
            missing or malformed.
        """
        from loop_control_plane.saml_okta import OktaMetadataError

        try:
            return self._delegate.parse(xml_bytes)
        except OktaMetadataError as exc:
            raise GoogleMetadataError(str(exc)) from exc
