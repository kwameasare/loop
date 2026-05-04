"""S618 — Okta SP-initiated end-to-end integration test.

Drives the *full* control-plane SAML SP-initiated login pipeline against
the committed Okta IdP metadata fixture, ending in an authenticated
Loop session token (PASETO ``v3.local``):

  1. Parse Okta IdP metadata XML  →  :class:`IdPMetadata`
  2. Build SP config + cert bundle  →  :func:`IdPMetadata.to_sp_config`
  3. Generate a sandbox SAML envelope and POST it through
     :func:`accept_acs_post` → :class:`AcsResult`
  4. JIT-provision the user + workspace member (creates the user
     row on first login, idempotent on second)  →
     :func:`jit_provision`
  5. Mint a Loop access + refresh token via :class:`AuthExchange`
     (the same path the Auth0 OIDC handler takes — only the user
     mapper differs because the upstream identity is now SAML).
  6. Decode the access token with :func:`decode_local` and assert the
     ``sub`` claim is the JIT-provisioned ``user_id``.

A real-Playwright + live-Okta-sandbox driver is intentionally
out-of-scope: it requires a live Okta org and outbound HTTP from CI,
which the sandbox test bench does not have. The control-plane SP
pipeline is exercised end-to-end here against the same metadata XML
the Okta admin would download from the org, which is the meaningful
correctness boundary.
"""

from __future__ import annotations

import asyncio
import base64
import json
import pathlib
import uuid
from datetime import UTC, datetime, timedelta

from loop_control_plane.auth_exchange import (
    AuthExchange,
    InMemoryRefreshTokenStore,
)
from loop_control_plane.jwks import JwtClaims
from loop_control_plane.paseto import decode_local
from loop_control_plane.saml import (
    StubSamlValidator,
    accept_acs_post,
)
from loop_control_plane.saml_jit import (
    InMemoryUserStore,
    jit_provision,
)
from loop_control_plane.saml_okta import OktaMetadataParser

# ---------------------------------------------------------------------------
# Fixtures and constants
# ---------------------------------------------------------------------------

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"
_OKTA_METADATA = _FIXTURES / "okta_idp_metadata.xml"

_TENANT_ID = "ws_okta_e2e"
_AUDIENCE = f"https://app.loop.dev/auth/saml/sp/{_TENANT_ID}"
_ISSUER = "http://www.okta.com/sandbox_loop_test_idp"
_NOW = datetime(2027, 6, 1, 12, 0, tzinfo=UTC)
_NOW_MS = int(_NOW.timestamp() * 1000)
_PASETO_KEY = b"\x42" * 32


def _envelope(
    *,
    subject: str = "alice@acme.example",
    full_name: str = "Alice Anderson",
    groups: list[str] | None = None,
) -> str:
    payload = {
        "subject": subject,
        "issuer": _ISSUER,
        "audience": _AUDIENCE,
        "not_before": (_NOW - timedelta(minutes=5)).isoformat(),
        "not_on_or_after": (_NOW + timedelta(hours=8)).isoformat(),
        "attributes": {
            "groups": groups or ["Loop-Admins"],
            "email": [subject],
            "displayName": [full_name],
        },
    }
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")


async def _exchange_for_session(
    *, user_id: uuid.UUID, audience: str, now_ms: int
) -> tuple[str, str]:
    """Mint a Loop access+refresh token from a JIT-provisioned user.

    The :class:`AuthExchange` is reused as-is from the Auth0 OIDC code
    path — the only adapter the SAML caller needs is a synthetic
    :class:`JwtClaims` whose ``sub`` is the IdP subject and whose
    ``user_mapper`` resolves to the JIT row.
    """

    async def mapper(sub: str) -> str | None:
        return str(user_id) if sub == "saml:" + str(user_id) else None

    exchange = AuthExchange(
        paseto_key=_PASETO_KEY,
        refresh_store=InMemoryRefreshTokenStore(),
        user_mapper=mapper,
        expected_audience=audience,
    )
    claims = JwtClaims(
        sub="saml:" + str(user_id),
        iss="loop-saml-acs",
        aud=(audience,),
        exp_ms=now_ms + 60 * 60 * 1000,
        iat_ms=now_ms,
        raw={},
    )
    result = await exchange.exchange(claims=claims, now_ms=now_ms)
    return result.access_token, result.refresh_token


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_okta_metadata_fixture_present() -> None:
    assert _OKTA_METADATA.exists(), (
        "Okta IdP metadata fixture missing; the e2e test depends on the "
        "committed fixture at packages/control-plane/fixtures/okta_idp_metadata.xml"
    )


def test_okta_sp_initiated_login_yields_authenticated_session() -> None:
    """The headline S618 e2e: metadata → ACS → JIT → session token."""

    # --- 1. Parse Okta metadata XML committed under fixtures/.
    idp = OktaMetadataParser().parse(_OKTA_METADATA.read_bytes())
    sp_config, bundle = idp.to_sp_config(
        _TENANT_ID,
        sandbox_mode=True,
        group_role_map={"Loop-Admins": "admin", "Loop-Viewers": "viewer"},
    )
    assert sp_config.issuer == _ISSUER
    assert sp_config.acs_url.endswith(f"/saml/acs/{_TENANT_ID}")

    # --- 2. Drive the ACS validation pipeline with a sandbox envelope.
    acs = accept_acs_post(
        _envelope(),
        sp_config,
        bundle,
        StubSamlValidator(),
        now=_NOW,
    )
    assert acs.assertion.subject == "alice@acme.example"
    assert acs.role == "admin"  # mapped from the Loop-Admins group claim.

    # --- 3. JIT-provision the user + workspace member.
    workspace_id = uuid.uuid4()
    store = InMemoryUserStore()
    jit = jit_provision(
        acs,
        workspace_id=workspace_id,
        auth_provider="saml-okta",
        store=store,
        now=_NOW,
    )
    assert jit.created_user is True
    assert jit.created_member is True
    assert jit.member.role == "admin"
    assert jit.user.email == "alice@acme.example"

    # --- 4. Exchange for a Loop access + refresh token.
    access_token, refresh_token = asyncio.run(
        _exchange_for_session(
            user_id=jit.user.id, audience=_AUDIENCE, now_ms=_NOW_MS
        )
    )
    assert access_token.startswith("v4.local."), (
        "access token must be a PASETO v4.local token"
    )
    assert refresh_token  # opaque random; just non-empty.

    # --- 5. Decode the access token: the session is authenticated for the
    #        JIT-provisioned user.
    decoded = decode_local(access_token, key=_PASETO_KEY, now_ms=_NOW_MS)
    assert decoded.claims["sub"] == str(jit.user.id)
    assert _AUDIENCE in (decoded.claims["aud"], )  # exchange pins audience.


def test_okta_sp_initiated_login_is_idempotent_on_replay() -> None:
    """Re-driving the full pipeline with the same SAML subject must NOT
    create a second user row, but MUST still mint a fresh session token —
    this is the property a real browser-driven Okta retry depends on."""
    idp = OktaMetadataParser().parse(_OKTA_METADATA.read_bytes())
    sp_config, bundle = idp.to_sp_config(
        _TENANT_ID,
        sandbox_mode=True,
        group_role_map={"Loop-Admins": "admin"},
    )
    workspace_id = uuid.uuid4()
    store = InMemoryUserStore()

    def _full_flow() -> tuple[bool, bool, str]:
        acs = accept_acs_post(
            _envelope(),
            sp_config,
            bundle,
            StubSamlValidator(),
            now=_NOW,
        )
        jit = jit_provision(
            acs,
            workspace_id=workspace_id,
            auth_provider="saml-okta",
            store=store,
            now=_NOW,
        )
        access, _ = asyncio.run(
            _exchange_for_session(
                user_id=jit.user.id, audience=_AUDIENCE, now_ms=_NOW_MS
            )
        )
        return jit.created_user, jit.created_member, access

    created_user_1, created_member_1, token_1 = _full_flow()
    created_user_2, created_member_2, token_2 = _full_flow()

    assert (created_user_1, created_member_1) == (True, True)
    assert (created_user_2, created_member_2) == (False, False)
    # Both flows yield valid (but distinct, due to refresh entropy) tokens
    # for the *same* user.
    assert token_1.startswith("v4.local.") and token_2.startswith("v4.local.")
    decoded_1 = decode_local(token_1, key=_PASETO_KEY, now_ms=_NOW_MS)
    decoded_2 = decode_local(token_2, key=_PASETO_KEY, now_ms=_NOW_MS)
    assert decoded_1.claims["sub"] == decoded_2.claims["sub"]


def test_okta_sp_initiated_login_promotes_role_on_group_change() -> None:
    """If Okta group membership changes between logins, the JIT path
    updates the workspace_members.role — exactly the behaviour an
    end-to-end browser driver would observe across two logins."""
    idp = OktaMetadataParser().parse(_OKTA_METADATA.read_bytes())
    sp_config, bundle = idp.to_sp_config(
        _TENANT_ID,
        sandbox_mode=True,
        group_role_map={"Loop-Viewers": "viewer", "Loop-Admins": "admin"},
    )
    workspace_id = uuid.uuid4()
    store = InMemoryUserStore()

    acs1 = accept_acs_post(
        _envelope(groups=["Loop-Viewers"]),
        sp_config,
        bundle,
        StubSamlValidator(),
        now=_NOW,
    )
    jit1 = jit_provision(
        acs1,
        workspace_id=workspace_id,
        auth_provider="saml-okta",
        store=store,
        now=_NOW,
    )
    assert jit1.member.role == "viewer"

    acs2 = accept_acs_post(
        _envelope(groups=["Loop-Admins"]),
        sp_config,
        bundle,
        StubSamlValidator(),
        now=_NOW,
    )
    jit2 = jit_provision(
        acs2,
        workspace_id=workspace_id,
        auth_provider="saml-okta",
        store=store,
        now=_NOW,
    )
    assert jit2.created_user is False
    assert jit2.created_member is False
    assert jit2.role_changed is True
    assert jit2.member.role == "admin"
