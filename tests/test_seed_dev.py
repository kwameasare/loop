"""Tests for ``tools/seed_dev.py``.

The script is referenced by ``make seed`` and is the documented way to
populate cp-api with a workspace + agent during local dev. The unit
under test here is the JWT minting helper — it must produce a token
that cp-api's ``HS256Verifier`` accepts. The full HTTP-exchange path
(`/v1/auth/exchange`, `POST /v1/workspaces`, ...) is integration-test
territory and runs against a live cp uvicorn in CI's compose smoke;
this file keeps the hermetic contract.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from loop_control_plane.auth import AuthError, HS256Verifier


def _load_seed_dev_module() -> object:
    """Load tools/seed_dev.py without it being on sys.path."""
    path = Path(__file__).resolve().parents[1] / "tools" / "seed_dev.py"
    spec = importlib.util.spec_from_file_location("loop_seed_dev", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("loop_seed_dev", module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def seed_dev() -> object:
    return _load_seed_dev_module()


def test_mint_local_jwt_produces_token_cp_verifier_accepts(seed_dev: object) -> None:
    """The whole point of the script: cp's HS256Verifier must accept
    the minted token without raising. If the wire format drifts (alg
    mismatch, claim shape, base64url padding) this test catches it."""
    secret = "test-secret-at-least-16-bytes-long"
    issuer = "https://loop.local/"
    audience = "loop-cp"
    token = seed_dev.mint_local_jwt(  # type: ignore[attr-defined]
        secret=secret,
        sub="dev@loop.local",
        issuer=issuer,
        audience=audience,
    )
    claims = HS256Verifier(secret=secret, issuer=issuer, audience=audience).verify(token)
    assert claims.sub == "dev@loop.local"
    assert claims.iss == issuer
    assert claims.aud == audience


def test_mint_local_jwt_rejects_empty_secret(seed_dev: object) -> None:
    """Empty secret would silently sign with b'' — that's a footgun
    we want to fail loudly on."""
    with pytest.raises(ValueError, match="LOOP_CP_LOCAL_JWT_SECRET"):
        seed_dev.mint_local_jwt(  # type: ignore[attr-defined]
            secret="",
            sub="x",
            issuer="https://loop.local/",
            audience="loop-cp",
        )


def test_mint_local_jwt_includes_email_claim_for_at_subjects(seed_dev: object) -> None:
    """When the sub looks like an email, surface it as the email claim
    so audit trails get a human-readable identity."""
    secret = "test-secret-at-least-16-bytes-long"
    token = seed_dev.mint_local_jwt(  # type: ignore[attr-defined]
        secret=secret,
        sub="alice@example.com",
        issuer="https://loop.local/",
        audience="loop-cp",
    )
    claims = HS256Verifier(
        secret=secret, issuer="https://loop.local/", audience="loop-cp"
    ).verify(token)
    assert claims.email == "alice@example.com"


def test_mint_local_jwt_rejects_after_wrong_audience(seed_dev: object) -> None:
    """A token minted for audience X must not verify against audience Y.
    Belt-and-suspenders: makes sure we're not accidentally signing with
    a constant audience."""
    secret = "test-secret-at-least-16-bytes-long"
    token = seed_dev.mint_local_jwt(  # type: ignore[attr-defined]
        secret=secret,
        sub="dev",
        issuer="https://loop.local/",
        audience="loop-cp",
    )
    with pytest.raises(AuthError):
        HS256Verifier(
            secret=secret, issuer="https://loop.local/", audience="some-other-audience"
        ).verify(token)
