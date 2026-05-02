"""Microsoft Entra ID SAML integration tests — S613.

Mirrors :mod:`test_okta_integration` but for Entra-shape metadata.
The sandbox fixture lives at
``packages/control-plane/fixtures/entra_idp_metadata.xml``.

End-to-end coverage:
  1. Parse Entra-schema metadata XML.
  2. Validate the issuer is ``https://sts.windows.net/<tenant>/`` and
     the SSO URL is on a ``login.microsoftonline.com`` host.
  3. Build a :class:`SamlSpConfig` whose ``group_role_map`` is keyed by
     Entra group **Object IDs** (GUIDs), not display names.
  4. Drive :func:`accept_acs_post` end-to-end through ``StubSamlValidator``
     with the Entra group claim URI.
"""

from __future__ import annotations

import base64
import json
import pathlib
from datetime import UTC, datetime, timedelta

import pytest
from loop_control_plane.saml import (
    SamlError,
    StubSamlValidator,
    accept_acs_post,
)
from loop_control_plane.saml_entra import (
    ENTRA_GROUPS_CLAIM,
    EntraMetadataError,
    EntraMetadataParser,
    build_entra_sp_config,
    extract_entra_tenant_id,
)

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"
_ENTRA_METADATA = _FIXTURES / "entra_idp_metadata.xml"

_TENANT_ID = "ws_entra_sandbox"
_ENTRA_TENANT_GUID = "00000000-0000-0000-0000-0000beefcafe"
_ENTRA_ISSUER = f"https://sts.windows.net/{_ENTRA_TENANT_GUID}/"
_ADMIN_GROUP_OID = "11111111-1111-1111-1111-111111111111"
_NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


def _stub_envelope(
    *,
    subject: str = "alice@contoso.com",
    issuer: str = _ENTRA_ISSUER,
    audience: str | None = None,
    groups: list[str] | None = None,
) -> str:
    if audience is None:
        audience = f"https://app.loop.dev/auth/saml/sp/{_TENANT_ID}"
    payload = {
        "subject": subject,
        "issuer": issuer,
        "audience": audience,
        "not_before": (_NOW - timedelta(minutes=5)).isoformat(),
        "not_on_or_after": (_NOW + timedelta(hours=8)).isoformat(),
        # Entra emits group OIDs under the WS-Fed claim URI.
        "attributes": {ENTRA_GROUPS_CLAIM: groups or [_ADMIN_GROUP_OID]},
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


def test_fixture_file_exists() -> None:
    assert _ENTRA_METADATA.exists(), f"missing fixture: {_ENTRA_METADATA}"


def test_parse_extracts_entra_tenant_guid() -> None:
    idp = EntraMetadataParser().parse(_ENTRA_METADATA.read_bytes())
    assert idp.entity_id == _ENTRA_ISSUER
    assert idp.sso_url_post.startswith(
        f"https://login.microsoftonline.com/{_ENTRA_TENANT_GUID}/"
    )
    assert idp.cert_pem_chain  # at least one signing cert
    assert extract_entra_tenant_id(idp) == _ENTRA_TENANT_GUID


def test_parse_rejects_okta_metadata_as_non_entra() -> None:
    """Pasting an Okta metadata blob into the Entra connector must
    fail loudly — otherwise an admin gets a misleading ``audience``
    mismatch later in the ACS flow."""
    okta_xml = (_FIXTURES / "okta_idp_metadata.xml").read_bytes()
    with pytest.raises(EntraMetadataError):
        EntraMetadataParser().parse(okta_xml)


def test_build_sp_config_rejects_display_name_as_group_key() -> None:
    """Common admin error: copying the group's display name from
    Azure Portal instead of its Object ID GUID."""
    idp = EntraMetadataParser().parse(_ENTRA_METADATA.read_bytes())
    with pytest.raises(EntraMetadataError, match="not a GUID"):
        build_entra_sp_config(
            idp,
            tenant_id=_TENANT_ID,
            group_object_id_to_role={"Loop-Admins": "admin"},
        )


def test_full_acs_loop_with_entra_group_oid_mapping() -> None:
    idp = EntraMetadataParser().parse(_ENTRA_METADATA.read_bytes())
    cfg, bundle = build_entra_sp_config(
        idp,
        tenant_id=_TENANT_ID,
        default_role="viewer",
        group_object_id_to_role={_ADMIN_GROUP_OID: "admin"},
        sandbox_mode=True,
    )
    # The IdP's claim URI is what the SP must look up — confirm the
    # config preserved the OID-keyed mapping.
    assert any(m.group == _ADMIN_GROUP_OID for m in cfg.group_role_map)

    result = accept_acs_post(
        saml_response_b64=_stub_envelope(),
        sp_config=cfg,
        cert_bundle=bundle,
        validator=StubSamlValidator(),
        now=_NOW,
    )
    assert result.role == "admin"
    assert result.assertion.subject == "alice@contoso.com"
    assert result.assertion.issuer == _ENTRA_ISSUER


def test_acs_rejects_wrong_issuer() -> None:
    """If the IdP-signed assertion claims a different issuer than the
    metadata, ``accept_acs_post`` must fail."""
    idp = EntraMetadataParser().parse(_ENTRA_METADATA.read_bytes())
    cfg, bundle = build_entra_sp_config(
        idp,
        tenant_id=_TENANT_ID,
        sandbox_mode=True,
    )
    with pytest.raises(SamlError):
        accept_acs_post(
            saml_response_b64=_stub_envelope(
                issuer="https://sts.windows.net/deadbeef-dead-beef-dead-beefdeadbeef/"
            ),
            sp_config=cfg,
            cert_bundle=bundle,
            validator=StubSamlValidator(),
            now=_NOW,
        )


def test_extract_tenant_id_rejects_non_entra_issuer() -> None:
    from loop_control_plane.saml_entra import IdPMetadata

    fake = IdPMetadata(
        entity_id="http://www.okta.com/sandbox",
        sso_url_post="https://example.com/sso",
        sso_url_redirect=None,
        cert_pem_chain=["-----BEGIN CERTIFICATE-----\nA\n-----END CERTIFICATE-----"],
    )
    with pytest.raises(EntraMetadataError):
        extract_entra_tenant_id(fake)
