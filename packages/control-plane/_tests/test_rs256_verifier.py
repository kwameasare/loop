"""RS256/JWKS verifier tests (vega #11).

We generate an RSA key pair at test time, sign JWTs with the private
half, and feed the public half through a stub :class:`JwksFetcher`.
That lets the verifier cover the whole production code path
(signature verify, kid lookup, kid rotation, expired keyset) without
network access or a fixed test key checked into the repo.
"""

from __future__ import annotations

import base64
import json
import time

import pytest
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.hashes import SHA256
from loop_control_plane.auth import (
    AuthError,
    IdentityClaims,
    JwksClient,
    RS256Verifier,
)

ISSUER = "https://example.auth0.com/"
AUDIENCE = "loop-cp-api"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _int_to_b64url(value: int) -> str:
    n_bytes = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return _b64url(n_bytes)


def _gen_keypair() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _public_jwk(private_key: rsa.RSAPrivateKey, kid: str) -> dict[str, str]:
    public = private_key.public_key()
    numbers = public.public_numbers()
    return {
        "kty": "RSA",
        "kid": kid,
        "alg": "RS256",
        "use": "sig",
        "n": _int_to_b64url(numbers.n),
        "e": _int_to_b64url(numbers.e),
    }


def _sign_token(
    private_key: rsa.RSAPrivateKey,
    *,
    kid: str,
    claims: dict[str, object],
    alg: str = "RS256",
) -> str:
    header = _b64url(json.dumps({"alg": alg, "kid": kid, "typ": "JWT"}).encode())
    body = _b64url(json.dumps(claims, separators=(",", ":")).encode())
    signing_input = f"{header}.{body}".encode()
    signature = private_key.sign(signing_input, padding.PKCS1v15(), SHA256())
    return f"{header}.{body}.{_b64url(signature)}"


def _claims(**overrides: object) -> dict[str, object]:
    now = int(time.time())
    base: dict[str, object] = {
        "sub": "auth0|user-1",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": now + 3600,
        "iat": now,
        "email": "alice@example.com",
        "scope": "read:agents write:agents",
    }
    base.update(overrides)
    return base


def _verifier(jwks_doc: dict[str, object]) -> RS256Verifier:
    return RS256Verifier(
        jwks=JwksClient(lambda: jwks_doc),
        issuer=ISSUER,
        audience=AUDIENCE,
    )


def test_round_trip_returns_identity_claims() -> None:
    key = _gen_keypair()
    jwks = {"keys": [_public_jwk(key, "kid-1")]}
    verifier = _verifier(jwks)
    token = _sign_token(key, kid="kid-1", claims=_claims())
    claims = verifier.verify(token)
    assert isinstance(claims, IdentityClaims)
    assert claims.sub == "auth0|user-1"
    assert claims.iss == ISSUER
    assert claims.aud == AUDIENCE
    assert "read:agents" in claims.scopes


def test_rejects_unknown_kid_and_does_not_loop_on_refetch() -> None:
    """If the kid isn't in the keyset (ever), we surface ``unknown kid``
    after exactly one refresh — not an infinite loop."""
    key = _gen_keypair()
    jwks = {"keys": [_public_jwk(key, "kid-1")]}
    fetch_calls = {"n": 0}

    def fetcher() -> dict[str, object]:
        fetch_calls["n"] += 1
        return jwks

    verifier = RS256Verifier(
        jwks=JwksClient(fetcher),
        issuer=ISSUER,
        audience=AUDIENCE,
    )
    token = _sign_token(key, kid="kid-rotated-out", claims=_claims())
    with pytest.raises(AuthError, match="unknown kid"):
        verifier.verify(token)
    # The cache miss triggered one refresh; we don't loop forever.
    assert fetch_calls["n"] == 1


def test_rejects_bad_signature() -> None:
    """A token signed by an attacker's key won't match the published JWK."""
    legit = _gen_keypair()
    attacker = _gen_keypair()
    jwks = {"keys": [_public_jwk(legit, "kid-1")]}
    verifier = _verifier(jwks)
    forged = _sign_token(attacker, kid="kid-1", claims=_claims())
    with pytest.raises(AuthError, match="bad signature"):
        verifier.verify(forged)


def test_rejects_expired_token() -> None:
    key = _gen_keypair()
    jwks = {"keys": [_public_jwk(key, "kid-1")]}
    verifier = _verifier(jwks)
    expired = _sign_token(
        key,
        kid="kid-1",
        claims=_claims(exp=int(time.time()) - 600),
    )
    with pytest.raises(AuthError, match="expired"):
        verifier.verify(expired)


def test_rejects_issuer_mismatch() -> None:
    key = _gen_keypair()
    jwks = {"keys": [_public_jwk(key, "kid-1")]}
    verifier = _verifier(jwks)
    bad = _sign_token(
        key,
        kid="kid-1",
        claims=_claims(iss="https://attacker.example/"),
    )
    with pytest.raises(AuthError, match="issuer mismatch"):
        verifier.verify(bad)


def test_rejects_audience_mismatch() -> None:
    key = _gen_keypair()
    jwks = {"keys": [_public_jwk(key, "kid-1")]}
    verifier = _verifier(jwks)
    bad = _sign_token(
        key,
        kid="kid-1",
        claims=_claims(aud="some-other-app"),
    )
    with pytest.raises(AuthError, match="audience mismatch"):
        verifier.verify(bad)


def test_rejects_alg_confusion_attack() -> None:
    """A JWT with ``alg: none`` or ``alg: HS256`` MUST be rejected
    even if the body otherwise looks valid. This is the classic JWT
    library bug — the alg-confusion CVE — and we have to test for it
    explicitly because cryptography won't catch it for us."""
    key = _gen_keypair()
    jwks = {"keys": [_public_jwk(key, "kid-1")]}
    verifier = _verifier(jwks)
    bad = _sign_token(key, kid="kid-1", claims=_claims(), alg="HS256")
    with pytest.raises(AuthError, match="unsupported alg"):
        verifier.verify(bad)


def test_picks_up_rotated_keyset_after_ttl() -> None:
    """Keysets get cached for ``ttl_seconds``. After a rotation we
    should pick up the new key on the next request that misses the
    cache (i.e., uses the new kid)."""
    old_key = _gen_keypair()
    new_key = _gen_keypair()
    state = {"keys": [_public_jwk(old_key, "kid-old")]}

    def fetcher() -> dict[str, object]:
        return state

    verifier = RS256Verifier(
        jwks=JwksClient(fetcher),
        issuer=ISSUER,
        audience=AUDIENCE,
    )
    # First request signs with the OLD key — works.
    verifier.verify(_sign_token(old_key, kid="kid-old", claims=_claims()))
    # Rotate: the IdP now publishes BOTH keys briefly (overlap), then
    # eventually only the new one. We mimic the steady state: only
    # the new key is published.
    state["keys"] = [_public_jwk(new_key, "kid-new")]
    # Second request signed with the new key triggers a refresh and
    # succeeds — the verifier picks up the rotated keyset without a
    # process restart.
    verifier.verify(_sign_token(new_key, kid="kid-new", claims=_claims()))


def test_caches_keys_within_ttl_to_avoid_per_request_jwks_fetch() -> None:
    """JWKS fetches are expensive (network). The cache must satisfy
    repeated lookups for the same kid without re-fetching, otherwise
    we'd hammer the IdP on every request."""
    key = _gen_keypair()
    jwks = {"keys": [_public_jwk(key, "kid-1")]}
    fetch_calls = {"n": 0}

    def fetcher() -> dict[str, object]:
        fetch_calls["n"] += 1
        return jwks

    verifier = RS256Verifier(
        jwks=JwksClient(fetcher, ttl_seconds=300.0),
        issuer=ISSUER,
        audience=AUDIENCE,
    )
    for _ in range(10):
        verifier.verify(_sign_token(key, kid="kid-1", claims=_claims()))
    # Exactly ONE fetch — the first verify primed the cache, the
    # other nine hit the cache.
    assert fetch_calls["n"] == 1
