"""Hermetic tests for :func:`build_token_verifier`.

Confirms the env-var dispatch (RS256/Auth0 vs. HS256/dev) without
touching the network. The RS256 signature path itself has dedicated
coverage in :mod:`test_rs256_verifier`.
"""

from __future__ import annotations

import pytest

from loop_control_plane.auth import (
    AuthError,
    HS256Verifier,
    RS256Verifier,
    build_token_verifier,
)


def test_picks_hs256_when_no_auth0_domain() -> None:
    verifier = build_token_verifier(
        auth0_domain=None,
        auth0_audience=None,
        hs256_secret="dev-secret",
        hs256_issuer="https://loop.local/",
        hs256_audience="loop-cp",
    )
    assert isinstance(verifier, HS256Verifier)


def test_picks_rs256_when_auth0_domain_set() -> None:
    verifier = build_token_verifier(
        auth0_domain="dev-tenant.us.auth0.com",
        auth0_audience="https://loop.ai",
        hs256_secret="dev-secret",
        hs256_issuer="https://loop.local/",
        hs256_audience="loop-cp",
    )
    assert isinstance(verifier, RS256Verifier)
    # Derived issuer should follow the Auth0 convention.
    assert verifier._issuer == "https://dev-tenant.us.auth0.com/"  # type: ignore[attr-defined]
    assert verifier._audience == "https://loop.ai"  # type: ignore[attr-defined]


def test_rs256_strips_trailing_slash_in_domain() -> None:
    verifier = build_token_verifier(
        auth0_domain="dev-tenant.us.auth0.com/",
        auth0_audience="https://loop.ai",
        hs256_secret="",
        hs256_issuer="",
        hs256_audience="",
    )
    assert verifier._issuer == "https://dev-tenant.us.auth0.com/"  # type: ignore[attr-defined]


def test_rs256_requires_audience() -> None:
    with pytest.raises(AuthError, match="LOOP_AUTH0_CLIENT_ID"):
        build_token_verifier(
            auth0_domain="dev-tenant.us.auth0.com",
            auth0_audience=None,
            hs256_secret="dev-secret",
            hs256_issuer="https://loop.local/",
            hs256_audience="loop-cp",
        )


def test_hs256_requires_secret() -> None:
    with pytest.raises(AuthError, match="LOOP_CP_LOCAL_JWT_SECRET"):
        build_token_verifier(
            auth0_domain=None,
            auth0_audience=None,
            hs256_secret="",
            hs256_issuer="https://loop.local/",
            hs256_audience="loop-cp",
        )
