"""Google Workspace SAML integration tests — S614.

Mirrors :mod:`test_okta_integration` and :mod:`test_entra_integration`
for Google-shape metadata.

End-to-end coverage:
  1. Parse Google-schema metadata XML.
  2. Validate the issuer is the Google IdP entity ID format and the
     SSO URL ``idpid`` query parameter matches.
  3. Build a :class:`SamlSpConfig` whose ``group_role_map`` is keyed by
     **group email addresses** (Google Workspace's natural format).
  4. Drive :func:`accept_acs_post` end-to-end through ``StubSamlValidator``.
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
from loop_control_plane.saml_google import (
    GOOGLE_DEFAULT_GROUPS_ATTRIBUTE,
    GoogleMetadataError,
    GoogleMetadataParser,
    build_google_sp_config,
    extract_google_idp_id,
)

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"
_GOOGLE_METADATA = _FIXTURES / "google_idp_metadata.xml"

_TENANT_ID = "ws_google_sandbox"
_IDPID = "C0sandbox42"
_GOOGLE_ISSUER = f"https://accounts.google.com/o/saml2?idpid={_IDPID}"
_ADMIN_GROUP_EMAIL = "loop-admins@example.com"
_NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


def _stub_envelope(
    *,
    subject: str = "alice@example.com",
    issuer: str = _GOOGLE_ISSUER,
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
        "attributes": {
            GOOGLE_DEFAULT_GROUPS_ATTRIBUTE: groups or [_ADMIN_GROUP_EMAIL],
        },
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


def test_fixture_file_exists() -> None:
    assert _GOOGLE_METADATA.exists()


def test_parse_extracts_google_idpid() -> None:
    idp = GoogleMetadataParser().parse(_GOOGLE_METADATA.read_bytes())
    assert idp.entity_id == _GOOGLE_ISSUER
    assert idp.sso_url_post.startswith(
        "https://accounts.google.com/o/saml2/idp?idpid="
    )
    assert idp.cert_pem_chain
    assert extract_google_idp_id(idp) == _IDPID


def test_parse_rejects_okta_metadata() -> None:
    with pytest.raises(GoogleMetadataError):
        GoogleMetadataParser().parse(
            (_FIXTURES / "okta_idp_metadata.xml").read_bytes()
        )


def test_parse_rejects_entra_metadata() -> None:
    with pytest.raises(GoogleMetadataError):
        GoogleMetadataParser().parse(
            (_FIXTURES / "entra_idp_metadata.xml").read_bytes()
        )


def test_build_sp_config_rejects_non_email_group_key() -> None:
    idp = GoogleMetadataParser().parse(_GOOGLE_METADATA.read_bytes())
    with pytest.raises(GoogleMetadataError, match="not an email"):
        build_google_sp_config(
            idp,
            tenant_id=_TENANT_ID,
            group_email_to_role={"Loop-Admins": "admin"},
        )


def test_full_acs_loop_with_group_email_mapping() -> None:
    idp = GoogleMetadataParser().parse(_GOOGLE_METADATA.read_bytes())
    cfg, bundle = build_google_sp_config(
        idp,
        tenant_id=_TENANT_ID,
        default_role="viewer",
        group_email_to_role={_ADMIN_GROUP_EMAIL: "admin"},
        sandbox_mode=True,
    )
    result = accept_acs_post(
        saml_response_b64=_stub_envelope(),
        sp_config=cfg,
        cert_bundle=bundle,
        validator=StubSamlValidator(),
        now=_NOW,
    )
    assert result.role == "admin"


def test_acs_falls_back_to_default_role_for_unmapped_group() -> None:
    idp = GoogleMetadataParser().parse(_GOOGLE_METADATA.read_bytes())
    cfg, bundle = build_google_sp_config(
        idp,
        tenant_id=_TENANT_ID,
        default_role="viewer",
        group_email_to_role={_ADMIN_GROUP_EMAIL: "admin"},
        sandbox_mode=True,
    )
    result = accept_acs_post(
        saml_response_b64=_stub_envelope(groups=["other@example.com"]),
        sp_config=cfg,
        cert_bundle=bundle,
        validator=StubSamlValidator(),
        now=_NOW,
    )
    assert result.role == "viewer"


def test_acs_rejects_wrong_issuer() -> None:
    idp = GoogleMetadataParser().parse(_GOOGLE_METADATA.read_bytes())
    cfg, bundle = build_google_sp_config(
        idp,
        tenant_id=_TENANT_ID,
        sandbox_mode=True,
    )
    with pytest.raises(SamlError):
        accept_acs_post(
            saml_response_b64=_stub_envelope(
                issuer="https://accounts.google.com/o/saml2?idpid=other",
            ),
            sp_config=cfg,
            cert_bundle=bundle,
            validator=StubSamlValidator(),
            now=_NOW,
        )


def test_extract_idpid_rejects_non_google_issuer() -> None:
    from loop_control_plane.saml_google import IdPMetadata

    fake = IdPMetadata(
        entity_id="https://sts.windows.net/00000000-0000-0000-0000-000000000000/",
        sso_url_post="https://login.microsoftonline.com/x/saml2",
        sso_url_redirect=None,
        cert_pem_chain=["-----BEGIN CERTIFICATE-----\nA\n-----END CERTIFICATE-----"],
    )
    with pytest.raises(GoogleMetadataError):
        extract_google_idp_id(fake)
