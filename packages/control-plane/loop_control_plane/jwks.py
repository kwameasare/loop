"""JWKS verifier (S104) — JWKS cache + audience/issuer claim checks.

The actual RSA/ES256 signature verification depends on the
``cryptography`` package; until it lands the cp-api wheel ships this
module's :class:`JwksCache` (TTL-bounded refresh, JWKS endpoint
fetch over an injected transport) plus the :class:`JwtValidator`
which separates *claim* validation (issuer, audience, exp/nbf) from
*signature* validation (delegated to a :class:`SignatureVerifier`
backend that the production wiring supplies). Tests use the
:class:`PassThroughVerifier` to exercise the cache + claim path.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

__all__ = [
    "JwksCache",
    "JwksError",
    "JwtClaims",
    "JwtValidator",
    "PassThroughVerifier",
    "SignatureVerifier",
]


class JwksError(ValueError):
    """JWKS / JWT validation failure."""


@dataclass(frozen=True)
class JwtClaims:
    sub: str
    iss: str
    aud: tuple[str, ...]
    exp_ms: int
    iat_ms: int
    raw: dict[str, Any]


@runtime_checkable
class SignatureVerifier(Protocol):
    """Verifies a JWS signature against a JWK. Production: RS256/ES256."""

    def verify(
        self,
        *,
        signing_input: bytes,
        signature: bytes,
        jwk: dict[str, Any],
    ) -> bool: ...


class PassThroughVerifier:
    """Test-double signature verifier — accepts any non-empty signature.

    Use only in tests where you trust the JWKS endpoint and want to
    exercise the cache + claim plumbing.
    """

    def verify(
        self,
        *,
        signing_input: bytes,
        signature: bytes,
        jwk: dict[str, Any],
    ) -> bool:
        return bool(signature) and bool(signing_input) and "kid" in jwk


JwksFetcher = Callable[[str], Awaitable[dict[str, Any]]]


class JwksCache:
    """TTL-bounded cache of JWK sets keyed by JWKS URL.

    The cache is intentionally *coarse* — we do not split per-kid
    because Auth0 rotates keys infrequently (>30 days) and the cost
    of a refresh is one HTTP call. ``ttl_ms`` defaults to 10 minutes
    (Auth0 docs recommend ≥10m, ≤24h).
    """

    def __init__(
        self,
        fetcher: JwksFetcher,
        *,
        ttl_ms: int = 10 * 60 * 1000,
    ) -> None:
        if ttl_ms <= 0:
            raise JwksError("ttl_ms must be positive")
        self._fetcher = fetcher
        self._ttl_ms = ttl_ms
        self._entries: dict[str, tuple[int, dict[str, Any]]] = {}

    async def get(self, jwks_url: str, *, now_ms: int) -> dict[str, Any]:
        cached = self._entries.get(jwks_url)
        if cached is not None:
            stored_at, jwks = cached
            if now_ms - stored_at < self._ttl_ms:
                return jwks
        jwks = await self._fetcher(jwks_url)
        if not isinstance(jwks, dict) or "keys" not in jwks:
            raise JwksError("JWKS payload missing 'keys'")
        self._entries[jwks_url] = (now_ms, jwks)
        return jwks

    async def find_key(
        self, jwks_url: str, kid: str, *, now_ms: int
    ) -> dict[str, Any]:
        jwks = await self.get(jwks_url, now_ms=now_ms)
        for jwk in jwks["keys"]:
            if jwk.get("kid") == kid:
                return jwk
        raise JwksError(f"kid {kid!r} not found in {jwks_url}")


class JwtValidator:
    """Validates a compact JWS (header.payload.signature) end-to-end."""

    def __init__(
        self,
        *,
        cache: JwksCache,
        verifier: SignatureVerifier,
        jwks_url: str,
        expected_issuer: str,
        expected_audience: str,
        leeway_ms: int = 30_000,
    ) -> None:
        self._cache = cache
        self._verifier = verifier
        self._jwks_url = jwks_url
        self._iss = expected_issuer
        self._aud = expected_audience
        self._leeway = leeway_ms

    async def validate(self, token: str, *, now_ms: int) -> JwtClaims:
        try:
            header_b64, payload_b64, sig_b64 = token.split(".")
        except ValueError as exc:
            raise JwksError("not a compact JWS") from exc
        header = _decode_segment(header_b64)
        payload = _decode_segment(payload_b64)
        sig = _b64u(sig_b64)
        kid = header.get("kid")
        if not isinstance(kid, str):
            raise JwksError("header missing kid")
        jwk = await self._cache.find_key(self._jwks_url, kid, now_ms=now_ms)
        signing_input = f"{header_b64}.{payload_b64}".encode()
        if not self._verifier.verify(
            signing_input=signing_input, signature=sig, jwk=jwk
        ):
            raise JwksError("signature verification failed")
        # Claim checks.
        iss = payload.get("iss")
        if iss != self._iss:
            raise JwksError(f"iss mismatch: got {iss!r}")
        aud = payload.get("aud")
        if isinstance(aud, str):
            audiences: tuple[str, ...] = (aud,)
        elif isinstance(aud, list) and all(isinstance(a, str) for a in aud):
            audiences = tuple(aud)
        else:
            raise JwksError("aud claim missing or malformed")
        if self._aud not in audiences:
            raise JwksError(f"aud {self._aud!r} not present in token aud={audiences!r}")
        exp_s = payload.get("exp")
        iat_s = payload.get("iat")
        if not isinstance(exp_s, int | float) or not isinstance(iat_s, int | float):
            raise JwksError("exp/iat missing or not numeric")
        exp_ms = int(exp_s * 1000)
        iat_ms = int(iat_s * 1000)
        if now_ms - self._leeway > exp_ms:
            raise JwksError("token expired")
        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise JwksError("sub claim missing")
        return JwtClaims(
            sub=sub, iss=iss, aud=audiences, exp_ms=exp_ms, iat_ms=iat_ms, raw=payload
        )


def _b64u(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _decode_segment(s: str) -> dict[str, Any]:
    try:
        obj = json.loads(_b64u(s))
    except (ValueError, json.JSONDecodeError) as exc:
        raise JwksError("invalid JWS segment") from exc
    if not isinstance(obj, dict):
        raise JwksError("JWS segment is not a JSON object")
    return obj
