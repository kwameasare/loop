"""Pass6 control-plane tests: PASETO local, JWKS, ApiKey middleware."""

from __future__ import annotations

import json

import pytest
from loop_control_plane.api_key_middleware import (
    ApiKeyMiddleware,
    extract_bearer,
)
from loop_control_plane.api_keys import ApiKeyService
from loop_control_plane.jwks import (
    JwksCache,
    JwksError,
    JwtValidator,
    PassThroughVerifier,
)
from loop_control_plane.paseto import (
    TokenExpired,
    TokenInvalid,
    TokenNotYetValid,
    decode_local,
    encode_local,
)

# --- PASETO ----------------------------------------------------------------

KEY = b"k" * 32


def test_paseto_round_trip_basic() -> None:
    tok = encode_local(
        {"sub": "user_1", "ws": "abc"},
        key=KEY,
        now_ms=1_000,
        expires_in_ms=60_000,
    )
    parsed = decode_local(tok, key=KEY, now_ms=1_500)
    assert parsed.claims["sub"] == "user_1"
    assert parsed.claims["exp"] == 61_000
    assert parsed.kid is None


def test_paseto_with_footer_and_kid() -> None:
    tok = encode_local(
        {"sub": "u"},
        key=KEY,
        now_ms=0,
        expires_in_ms=10_000,
        kid="key-2026-04",
    )
    parsed = decode_local(tok, key=KEY, now_ms=0)
    assert parsed.kid == "key-2026-04"


def test_paseto_tamper_rejected() -> None:
    tok = encode_local({"x": "1"}, key=KEY, now_ms=0, expires_in_ms=60_000)
    # Flip one char in the body.
    bad = tok[:-3] + ("A" if tok[-3] != "A" else "B") + tok[-2:]
    with pytest.raises(TokenInvalid):
        decode_local(bad, key=KEY, now_ms=0)


def test_paseto_wrong_key_rejected() -> None:
    tok = encode_local({"x": "1"}, key=KEY, now_ms=0, expires_in_ms=60_000)
    with pytest.raises(TokenInvalid):
        decode_local(tok, key=b"x" * 32, now_ms=0)


def test_paseto_expired() -> None:
    tok = encode_local({"x": "1"}, key=KEY, now_ms=0, expires_in_ms=10)
    with pytest.raises(TokenExpired):
        decode_local(tok, key=KEY, now_ms=10_000_000)


def test_paseto_not_yet_valid() -> None:
    tok = encode_local(
        {"x": "1"},
        key=KEY,
        now_ms=10_000_000,
        expires_in_ms=60_000,
        not_before_ms=1_000_000,
    )
    with pytest.raises(TokenNotYetValid):
        decode_local(tok, key=KEY, now_ms=0)


def test_paseto_reserved_claim_collision() -> None:
    with pytest.raises(ValueError):
        encode_local(
            {"exp": 99},
            key=KEY,
            now_ms=0,
            expires_in_ms=60_000,
        )


# --- JWKS ------------------------------------------------------------------


def _b64(d: dict) -> str:
    import base64
    raw = json.dumps(d, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _make_jwt(*, kid: str, payload: dict) -> str:
    header = {"alg": "RS256", "kid": kid, "typ": "JWT"}
    return f"{_b64(header)}.{_b64(payload)}.c2ln"


async def _fetcher_factory(jwks: dict):
    async def _f(url: str) -> dict:
        return jwks
    return _f


@pytest.mark.asyncio
async def test_jwks_cache_hits_within_ttl() -> None:
    calls = {"n": 0}
    jwks = {"keys": [{"kid": "k1", "kty": "RSA"}]}

    async def fetcher(url: str) -> dict:
        calls["n"] += 1
        return jwks

    cache = JwksCache(fetcher, ttl_ms=1000)
    await cache.get("https://x", now_ms=0)
    await cache.get("https://x", now_ms=500)
    assert calls["n"] == 1
    await cache.get("https://x", now_ms=2000)
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_jwt_validator_happy_path() -> None:
    jwks = {"keys": [{"kid": "k1", "kty": "RSA"}]}

    async def fetcher(url: str) -> dict:
        return jwks

    cache = JwksCache(fetcher)
    validator = JwtValidator(
        cache=cache,
        verifier=PassThroughVerifier(),
        jwks_url="https://x",
        expected_issuer="https://issuer/",
        expected_audience="api://loop",
    )
    payload = {
        "sub": "user_1",
        "iss": "https://issuer/",
        "aud": ["api://loop", "api://other"],
        "exp": 1_000_000,
        "iat": 999_000,
    }
    token = _make_jwt(kid="k1", payload=payload)
    claims = await validator.validate(token, now_ms=999_500_000)
    assert claims.sub == "user_1"
    assert "api://loop" in claims.aud


@pytest.mark.asyncio
async def test_jwt_validator_rejects_wrong_audience() -> None:
    async def fetcher(url: str) -> dict:
        return {"keys": [{"kid": "k1", "kty": "RSA"}]}

    cache = JwksCache(fetcher)
    validator = JwtValidator(
        cache=cache,
        verifier=PassThroughVerifier(),
        jwks_url="https://x",
        expected_issuer="https://issuer/",
        expected_audience="api://loop",
    )
    payload = {
        "sub": "u",
        "iss": "https://issuer/",
        "aud": "api://other",
        "exp": 9_999_999_999,
        "iat": 1,
    }
    token = _make_jwt(kid="k1", payload=payload)
    with pytest.raises(JwksError, match="aud"):
        await validator.validate(token, now_ms=1_000)


@pytest.mark.asyncio
async def test_jwt_validator_unknown_kid() -> None:
    async def fetcher(url: str) -> dict:
        return {"keys": [{"kid": "k1", "kty": "RSA"}]}

    cache = JwksCache(fetcher)
    validator = JwtValidator(
        cache=cache,
        verifier=PassThroughVerifier(),
        jwks_url="https://x",
        expected_issuer="https://issuer/",
        expected_audience="api://loop",
    )
    token = _make_jwt(
        kid="other",
        payload={
            "sub": "u",
            "iss": "https://issuer/",
            "aud": "api://loop",
            "exp": 9_999_999_999,
            "iat": 1,
        },
    )
    with pytest.raises(JwksError, match="kid"):
        await validator.validate(token, now_ms=1_000)


# --- ApiKey middleware ----------------------------------------------------


def test_extract_bearer_variants() -> None:
    assert extract_bearer(None) is None
    assert extract_bearer("") is None
    assert extract_bearer("Basic abcd") is None
    assert extract_bearer("Bearer xyz") == "xyz"
    assert extract_bearer("Bearer   foo  ") == "foo"


@pytest.mark.asyncio
async def test_api_key_middleware_happy_path() -> None:
    from uuid import uuid4

    svc = ApiKeyService()
    issued = await svc.issue(
        workspace_id=uuid4(), name="ci", created_by="user@x"
    )
    mw = ApiKeyMiddleware(svc)
    decision = await mw.authenticate(f"Bearer {issued.plaintext}")
    assert decision.authorised
    assert decision.principal is not None
    assert decision.principal.workspace_id == issued.record.workspace_id


@pytest.mark.asyncio
async def test_api_key_middleware_missing_header() -> None:
    mw = ApiKeyMiddleware(ApiKeyService())
    decision = await mw.authenticate(None)
    assert not decision.authorised
    assert decision.error_code == "LOOP-AUTH-100"


@pytest.mark.asyncio
async def test_api_key_middleware_wrong_scheme() -> None:
    mw = ApiKeyMiddleware(ApiKeyService())
    decision = await mw.authenticate("Basic abc")
    assert decision.error_code == "LOOP-AUTH-101"


@pytest.mark.asyncio
async def test_api_key_middleware_not_loop_key() -> None:
    mw = ApiKeyMiddleware(ApiKeyService())
    decision = await mw.authenticate("Bearer foo_bar_123")
    assert decision.error_code == "LOOP-AUTH-101"


@pytest.mark.asyncio
async def test_api_key_middleware_unknown_key() -> None:
    mw = ApiKeyMiddleware(ApiKeyService())
    decision = await mw.authenticate("Bearer loop_sk_unknown_secret_123456789")
    assert decision.error_code == "LOOP-AUTH-102"
