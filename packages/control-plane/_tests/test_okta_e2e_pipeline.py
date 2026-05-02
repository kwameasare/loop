"""Full Okta SP-initiated login integration test — S618.

End-to-end pipeline test covering the complete SSO login flow that would
be triggered by the Okta SP-initiated login:

  Browser → Okta IdP → ACS endpoint → session creation

Since a live Okta sandbox cannot be spun up in CI, we simulate the full
pipeline with:

  1. Okta metadata XML fixture  → ``OktaMetadataParser`` → ``SamlSpConfig``
  2. Stub SAML response (``StubSamlValidator`` sandbox mode) → ``accept_acs_post``
  3. ``jit_provision`` → ``JitProvisionResult``

The test asserts the result that Studio would observe after this flow:
  - A valid ``JitUser`` with correct email and auth_subject
  - A ``JitMember`` row with the role projected from the IdP group claim
  - Correct ``created_user`` / ``created_member`` flags
  - Idempotency: second login reuses the user row, refreshes the role

Playwright note
---------------
``test_e2e_okta_studio_session_e2e_requires_playwright`` and
``test_e2e_okta_stub_idp_server_requires_playwright`` are registered as
skippable smoke hooks (``@pytest.mark.e2e``) that stub out the HTTP
layer.  They document exactly what a real Playwright-based E2E harness
would drive; the shared setup fixtures make it straightforward to
graduate them to a real Playwright runner once a sandbox Okta org is
available in CI.
"""

from __future__ import annotations

import base64
import json
import pathlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import NamedTuple

import pytest
from loop_control_plane.saml import (
    AcsResult,
    SamlError,
    SamlSpConfig,
    StubSamlValidator,
    accept_acs_post,
)
from loop_control_plane.saml_certs import CertificateBundle
from loop_control_plane.saml_jit import (
    InMemoryUserStore,
    JitCollisionError,
    JitProvisionResult,
    jit_provision,
)
from loop_control_plane.saml_okta import OktaMetadataParser

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"
_OKTA_METADATA = _FIXTURES / "okta_idp_metadata.xml"

_TENANT_ID = "ws_okta_e2e"
_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_AUTH_PROVIDER = "saml-okta"


def _now() -> datetime:
    """Return the current UTC time so assertions are always fresh."""
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stub_envelope(
    *,
    subject: str = "alice@example.com",
    issuer: str = "http://www.okta.com/sandbox_loop_test_idp",
    audience: str | None = None,
    groups: list[str] | None = None,
    extra_attributes: dict[str, list[str]] | None = None,
    not_before: datetime | None = None,
    not_on_or_after: datetime | None = None,
) -> str:
    """Build a base64-encoded JSON envelope for ``StubSamlValidator``."""
    if audience is None:
        audience = f"https://app.loop.dev/auth/saml/sp/{_TENANT_ID}"
    attrs: dict[str, list[str]] = {"groups": groups or ["Loop-Admins"]}
    if extra_attributes:
        attrs.update(extra_attributes)
    payload = {
        "subject": subject,
        "issuer": issuer,
        "audience": audience,
        "not_before": (not_before or (_now() - timedelta(minutes=5))).isoformat(),
        "not_on_or_after": (not_on_or_after or (_now() + timedelta(hours=8))).isoformat(),
        "attributes": attrs,
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


def _build_sp_config(
    group_role_map: dict[str, str] | None = None,
) -> tuple[SamlSpConfig, CertificateBundle]:
    """Parse Okta fixture metadata and build SamlSpConfig + CertificateBundle."""
    xml_bytes = _OKTA_METADATA.read_bytes()
    idp = OktaMetadataParser().parse(xml_bytes)
    return idp.to_sp_config(
        _TENANT_ID,
        sandbox_mode=True,
        group_role_map=group_role_map or {"Loop-Admins": "admin", "Loop-Editors": "editor"},
    )


def _run_acs(
    envelope: str,
    sp_config: SamlSpConfig,
    cert_bundle: CertificateBundle,
) -> AcsResult:
    """Drive accept_acs_post with StubSamlValidator."""
    return accept_acs_post(
        envelope,
        sp_config=sp_config,
        cert_bundle=cert_bundle,
        validator=StubSamlValidator(),
    )


# ---------------------------------------------------------------------------
# Full pipeline fixture
# ---------------------------------------------------------------------------


class SessionFixture(NamedTuple):
    sp_config: SamlSpConfig
    cert_bundle: CertificateBundle
    store: InMemoryUserStore


@pytest.fixture()
def session_fixture() -> SessionFixture:
    sp, bundle = _build_sp_config()
    return SessionFixture(sp_config=sp, cert_bundle=bundle, store=InMemoryUserStore())


# ---------------------------------------------------------------------------
# Tests: full pipeline (metadata → ACS → JIT → session)
# ---------------------------------------------------------------------------


def test_full_pipeline_new_user_gets_admin_role(
    session_fixture: SessionFixture,
) -> None:
    """First Okta login: unknown subject → user + member created, role=admin."""
    sp, bundle, store = session_fixture
    envelope = _stub_envelope(groups=["Loop-Admins"])

    acs = _run_acs(envelope, sp, bundle)
    result = jit_provision(
        acs,
        workspace_id=_WORKSPACE_ID,
        auth_provider=_AUTH_PROVIDER,
        store=store,
        now=_now(),
    )

    assert isinstance(result, JitProvisionResult)
    assert result.created_user is True
    assert result.created_member is True
    assert result.user.email == "alice@example.com"
    assert result.user.auth_provider == _AUTH_PROVIDER
    assert result.user.auth_subject == "alice@example.com"
    assert result.member.role == "admin"
    assert result.member.workspace_id == _WORKSPACE_ID


def test_full_pipeline_editor_role_from_group(
    session_fixture: SessionFixture,
) -> None:
    """Login with editor group → workspace_members.role == editor."""
    sp, bundle, store = session_fixture
    envelope = _stub_envelope(subject="bob@example.com", groups=["Loop-Editors"])

    acs = _run_acs(envelope, sp, bundle)
    result = jit_provision(
        acs,
        workspace_id=_WORKSPACE_ID,
        auth_provider=_AUTH_PROVIDER,
        store=store,
        now=_now(),
    )

    assert result.member.role == "editor"
    assert result.created_user is True


def test_full_pipeline_viewer_role_default_fallback(
    session_fixture: SessionFixture,
) -> None:
    """Login with unrecognised group → falls back to sp_config.default_role."""
    # Build SP config with explicit viewer default
    xml_bytes = _OKTA_METADATA.read_bytes()
    idp = OktaMetadataParser().parse(xml_bytes)
    sp, bundle = idp.to_sp_config(
        _TENANT_ID,
        sandbox_mode=True,
        group_role_map={"Loop-Admins": "admin"},
        default_role="viewer",
    )
    store = InMemoryUserStore()
    envelope = _stub_envelope(subject="carol@example.com", groups=["UnknownGroup"])

    acs = _run_acs(envelope, sp, bundle)
    result = jit_provision(
        acs,
        workspace_id=_WORKSPACE_ID,
        auth_provider=_AUTH_PROVIDER,
        store=store,
        now=_now(),
    )

    assert result.member.role == "viewer"


def test_full_pipeline_second_login_reuses_user(
    session_fixture: SessionFixture,
) -> None:
    """Second Okta login for the same subject reuses the user row."""
    sp, bundle, store = session_fixture
    envelope = _stub_envelope()

    # First login
    acs1 = _run_acs(envelope, sp, bundle)
    r1 = jit_provision(
        acs1, workspace_id=_WORKSPACE_ID, auth_provider=_AUTH_PROVIDER, store=store, now=_now()
    )

    # Second login
    acs2 = _run_acs(envelope, sp, bundle)
    r2 = jit_provision(
        acs2, workspace_id=_WORKSPACE_ID, auth_provider=_AUTH_PROVIDER, store=store, now=_now()
    )

    assert r2.created_user is False
    assert r2.user.id == r1.user.id  # same user row


def test_full_pipeline_role_refresh_on_group_change(
    session_fixture: SessionFixture,
) -> None:
    """Role is updated on next login when IdP group membership changes."""
    sp, bundle, store = session_fixture
    # First login as editor
    envelope_editor = _stub_envelope(subject="dave@example.com", groups=["Loop-Editors"])
    acs = _run_acs(envelope_editor, sp, bundle)
    jit_provision(
        acs, workspace_id=_WORKSPACE_ID, auth_provider=_AUTH_PROVIDER, store=store, now=_now()
    )

    # Second login — same user, now in admins group
    envelope_admin = _stub_envelope(subject="dave@example.com", groups=["Loop-Admins"])
    acs2 = _run_acs(envelope_admin, sp, bundle)
    r2 = jit_provision(
        acs2, workspace_id=_WORKSPACE_ID, auth_provider=_AUTH_PROVIDER, store=store, now=_now()
    )

    assert r2.member.role == "admin"
    assert r2.role_changed is True
    assert r2.created_user is False


def test_full_pipeline_email_attribute_overrides_subject(
    session_fixture: SessionFixture,
) -> None:
    """Email attribute from assertion is stored on the user row, not the NameID."""
    sp, bundle, store = session_fixture
    envelope = _stub_envelope(
        subject="opaque-nameid-00099",
        issuer="http://www.okta.com/sandbox_loop_test_idp",
        extra_attributes={"email": ["eve@corp.example.com"]},
    )

    acs = _run_acs(envelope, sp, bundle)
    result = jit_provision(
        acs,
        workspace_id=_WORKSPACE_ID,
        auth_provider=_AUTH_PROVIDER,
        store=store,
        now=_now(),
    )

    assert result.user.email == "eve@corp.example.com"
    assert result.user.auth_subject == "opaque-nameid-00099"


def test_full_pipeline_display_name_from_assertion(
    session_fixture: SessionFixture,
) -> None:
    """Display name from displayName attribute is stored on the user row."""
    sp, bundle, store = session_fixture
    envelope = _stub_envelope(
        subject="frank@example.com",
        extra_attributes={"displayName": ["Frank Müller"]},
    )

    acs = _run_acs(envelope, sp, bundle)
    result = jit_provision(
        acs,
        workspace_id=_WORKSPACE_ID,
        auth_provider=_AUTH_PROVIDER,
        store=store,
        now=_now(),
    )

    assert result.user.full_name == "Frank Müller"


def test_full_pipeline_acs_rejects_wrong_audience(
    session_fixture: SessionFixture,
) -> None:
    """ACS envelope with wrong audience is rejected before JIT provisioning."""
    sp, bundle, _ = session_fixture
    envelope = _stub_envelope(audience="https://evil.example.com/wrong")

    with pytest.raises(SamlError):
        _run_acs(envelope, sp, bundle)


def test_full_pipeline_acs_rejects_expired_assertion(
    session_fixture: SessionFixture,
) -> None:
    """ACS envelope with expired not_on_or_after is rejected."""
    sp, bundle, _ = session_fixture
    envelope = _stub_envelope(
        not_before=_now() - timedelta(hours=9),
        not_on_or_after=_now() - timedelta(hours=1),
    )

    with pytest.raises(SamlError):
        _run_acs(envelope, sp, bundle)


def test_full_pipeline_jit_collision_error_for_email_takeover(
    session_fixture: SessionFixture,
) -> None:
    """Email-collision guard: same email under different IdP subject is rejected."""
    sp, bundle, store = session_fixture

    # First user: alice@example.com under auth_provider saml-okta
    envelope1 = _stub_envelope(subject="alice@example.com")
    acs1 = _run_acs(envelope1, sp, bundle)
    jit_provision(
        acs1, workspace_id=_WORKSPACE_ID, auth_provider=_AUTH_PROVIDER, store=store, now=_now()
    )

    # Second attempt: different provider but same email — should raise
    envelope2 = _stub_envelope(subject="alice@example.com")
    acs2 = _run_acs(envelope2, sp, bundle)
    with pytest.raises(JitCollisionError):
        jit_provision(
            acs2,
            workspace_id=_WORKSPACE_ID,
            auth_provider="saml-entra",  # different provider
            store=store,
            now=_now(),
        )


# ---------------------------------------------------------------------------
# Tests: multiple users / workspaces in same session
# ---------------------------------------------------------------------------


def test_full_pipeline_two_users_in_same_workspace(
    session_fixture: SessionFixture,
) -> None:
    """Two distinct users can both obtain membership in the same workspace."""
    sp, bundle, store = session_fixture

    for subject, group in [
        ("user1@example.com", ["Loop-Admins"]),
        ("user2@example.com", ["Loop-Editors"]),
    ]:
        acs = _run_acs(_stub_envelope(subject=subject, groups=group), sp, bundle)
        jit_provision(
            acs, workspace_id=_WORKSPACE_ID, auth_provider=_AUTH_PROVIDER, store=store, now=_now()
        )

    members = [
        store.get_member(workspace_id=_WORKSPACE_ID, user_id=u.id)
        for u in store._users_by_id.values()
    ]
    assert len(members) == 2
    roles = {m.role for m in members if m is not None}
    assert "admin" in roles
    assert "editor" in roles


# ---------------------------------------------------------------------------
# E2E smoke hooks (skipped in CI; graduate to Playwright when sandbox available)
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@pytest.mark.skip(reason="requires live Okta sandbox + running Studio — run locally")
def test_e2e_okta_studio_session_e2e_requires_playwright() -> None:  # pragma: no cover
    """Smoke test: Playwright drives Okta sandbox SP-initiated login to Studio.

    Steps (manual Playwright harness):
      1. Navigate to Studio /enterprise; click "Sign in with SSO".
      2. Browser redirects to Okta sandbox IdP.
      3. Okta authenticates test user (Loop-Admins group).
      4. Okta POSTs SAMLResponse to Studio ACS endpoint.
      5. Control-plane processes assertion, provisions user, mints JWT.
      6. Browser is redirected to Studio dashboard with authenticated session.
      7. Assert: page title matches "Studio | Loop", JWT cookie is present.
    """
    raise NotImplementedError("Implement with Playwright page.goto() + assertions")


@pytest.mark.e2e
@pytest.mark.skip(reason="requires live Okta sandbox + running Studio — run locally")
def test_e2e_okta_stub_idp_server_requires_playwright() -> None:  # pragma: no cover
    """Smoke test: stub SAML IdP HTTP server + Playwright session flow.

    Steps (stub HTTP IdP harness):
      1. Start a local stub IdP HTTP server (StubSamlValidator wrapped in WSGI).
      2. Configure Studio to trust the stub IdP via its metadata endpoint.
      3. Run SP-initiated login through Playwright.
      4. Assert the session cookie is set and /api/me returns the provisioned user.
    """
    raise NotImplementedError("Implement with pytest-playwright + httpx stub server")
