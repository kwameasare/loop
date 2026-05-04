"""Auth: JWT verifiers with Auth0-shaped claims.

This module exposes two concrete verifiers behind the
:class:`TokenVerifier` Protocol:

  - :class:`HS256Verifier`: dev/test HMAC verifier. Lets the rest of
    the control plane build against the protocol without standing up
    Auth0.
  - :class:`RS256Verifier`: JWKS-backed RSA verifier (vega #11,
    block-prod). Production identity providers (Auth0, Okta, AWS
    Cognito, …) sign with RSA and publish their public key set at a
    well-known JWKS URL. The verifier fetches the keyset, caches it
    by ``kid`` with a TTL, and refreshes on cache miss so a key
    rotation eventually picks up the new key without a restart.

Nothing in the API layer depends on the verification mechanics — the
swap from dev HS256 to prod RS256 is wiring, not a code change in
the routes.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
from collections.abc import Callable, Sequence
from typing import Any, Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from pydantic import BaseModel, ConfigDict, Field


class AuthError(ValueError):
    """Raised when a token fails verification."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


class IdentityClaims(BaseModel):
    """Subset of an Auth0 access-token's verified claims."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    sub: str = Field(min_length=1)
    iss: str = Field(min_length=1)
    aud: str = Field(min_length=1)
    exp: int = Field(ge=0)
    iat: int = Field(ge=0)
    email: str | None = None
    scope: str = ""

    @property
    def scopes(self) -> tuple[str, ...]:
        return tuple(s for s in self.scope.split(" ") if s)


class TokenVerifier(Protocol):
    def verify(self, token: str) -> IdentityClaims: ...


class HS256Verifier:
    """Test/dev-only JWT verifier using HMAC-SHA256.

    Real deployments use :class:`RS256Verifier` against an IdP's JWKS
    URL -- this exists so the rest of the control plane can build
    against :class:`TokenVerifier` without standing up Auth0 first.
    """

    def __init__(
        self,
        *,
        secret: str,
        issuer: str,
        audience: str,
        leeway_seconds: int = 30,
    ) -> None:
        if not secret:
            raise ValueError("secret must be non-empty")
        self._secret = secret.encode("utf-8")
        self._issuer = issuer
        self._audience = audience
        self._leeway = leeway_seconds

    def sign(self, claims: dict[str, object]) -> str:
        """Helper for tests / dev fixtures to mint signed tokens."""
        header = _b64url_encode(b'{"alg":"HS256","typ":"JWT"}')
        body = _b64url_encode(json.dumps(claims, separators=(",", ":")).encode())
        signing_input = f"{header}.{body}".encode()
        sig = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        return f"{header}.{body}.{_b64url_encode(sig)}"

    def verify(self, token: str) -> IdentityClaims:
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthError("malformed token")
        header_b64, body_b64, sig_b64 = parts
        try:
            header = json.loads(_b64url_decode(header_b64))
        except (ValueError, json.JSONDecodeError) as exc:
            raise AuthError("malformed header") from exc
        if header.get("alg") != "HS256":
            raise AuthError("unsupported alg")
        signing_input = f"{header_b64}.{body_b64}".encode()
        expected = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        try:
            actual = _b64url_decode(sig_b64)
        except ValueError as exc:
            raise AuthError("malformed signature") from exc
        if not hmac.compare_digest(expected, actual):
            raise AuthError("bad signature")
        try:
            payload = json.loads(_b64url_decode(body_b64))
        except (ValueError, json.JSONDecodeError) as exc:
            raise AuthError("malformed body") from exc
        now = int(time.time())
        exp = int(payload.get("exp", 0))
        if exp and now > exp + self._leeway:
            raise AuthError("token expired")
        if payload.get("iss") != self._issuer:
            raise AuthError("issuer mismatch")
        aud = payload.get("aud")
        if isinstance(aud, list):
            if self._audience not in aud:
                raise AuthError("audience mismatch")
            payload["aud"] = self._audience
        elif aud != self._audience:
            raise AuthError("audience mismatch")
        # Drop any unknown fields rather than reject -- Auth0 emits
        # extras like azp, gty that we don't model.
        keep = {"sub", "iss", "aud", "exp", "iat", "email", "scope"}
        filtered = {k: v for k, v in payload.items() if k in keep}
        try:
            return IdentityClaims(**filtered)  # type: ignore[arg-type]
        except Exception as exc:
            raise AuthError(f"invalid claims: {exc}") from exc


def has_scope(claims: IdentityClaims, required: Sequence[str]) -> bool:
    have = set(claims.scopes)
    return all(s in have for s in required)


# ---------------------------------------------------------------------------
# RS256 / JWKS verifier (vega #11)
# ---------------------------------------------------------------------------


class JwksFetcher(Protocol):
    """Callable that fetches the raw JWKS document.

    Production wires this to an ``httpx`` GET against the IdP's
    well-known URL; tests inject a stub that returns a pre-built
    keyset so they don't need network access."""

    def __call__(self) -> dict[str, Any]: ...


class JwksClient:
    """Caches RSA public keys by ``kid`` with a TTL.

    The verifier asks for ``get(kid)`` per request. On miss we refetch
    the JWKS, populate the cache, and try again. A second miss after a
    fresh fetch is treated as ``unknown kid`` rather than a loop —
    that's what catches a rotated-out key whose JWTs are still in
    flight.

    The cache is process-local + thread-safe (sync ``threading.Lock``).
    For the cp this is fine: we have one auth verifier per process and
    JWT verification is on the auth hot path, so a Lock is cheaper
    than an asyncio.Lock and avoids forcing every caller into async.
    """

    def __init__(
        self,
        fetcher: JwksFetcher,
        *,
        ttl_seconds: float = 300.0,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._fetcher = fetcher
        self._ttl = ttl_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._keys: dict[str, rsa.RSAPublicKey] = {}
        self._fetched_at: float = 0.0

    def _refresh(self) -> None:
        document = self._fetcher()
        keys: dict[str, rsa.RSAPublicKey] = {}
        for jwk in document.get("keys", []):
            if jwk.get("kty") != "RSA":
                # We only support RSA. Other key types (EC, oct) are
                # left out of the cache so they're transparently
                # treated as unknown kids.
                continue
            kid = jwk.get("kid")
            if not isinstance(kid, str):
                continue
            try:
                keys[kid] = _rsa_public_key_from_jwk(jwk)
            except (ValueError, KeyError):
                # A malformed key shouldn't tank the whole keyset.
                continue
        with self._lock:
            self._keys = keys
            self._fetched_at = self._clock()

    def get(self, kid: str) -> rsa.RSAPublicKey:
        with self._lock:
            cached = self._keys.get(kid)
            age = self._clock() - self._fetched_at
        if cached is not None and age <= self._ttl:
            return cached
        # Cache miss OR stale: refresh once and retry.
        self._refresh()
        with self._lock:
            cached = self._keys.get(kid)
        if cached is None:
            raise AuthError(f"unknown kid {kid!r}")
        return cached


def _rsa_public_key_from_jwk(jwk: dict[str, Any]) -> rsa.RSAPublicKey:
    """Convert a JWK ``{n, e}`` pair into a cryptography RSA public key."""
    n = _b64url_decode_int(jwk["n"])
    e = _b64url_decode_int(jwk["e"])
    return rsa.RSAPublicNumbers(e=e, n=n).public_key()


def _b64url_decode_int(value: str) -> int:
    return int.from_bytes(_b64url_decode(value), "big")


class RS256Verifier:
    """Production JWT verifier: RS256 signatures verified against a
    JWKS-backed key set, with the same claim-shape contract as
    :class:`HS256Verifier`.

    Closes vega #11 (block-prod): the cp accepted only HS256 tokens,
    which forced any production IdP integration to share a symmetric
    secret. RS256 + JWKS is the standard for Auth0 / Okta / Cognito
    and lets us rotate keys without redeploying.
    """

    def __init__(
        self,
        *,
        jwks: JwksClient,
        issuer: str,
        audience: str,
        leeway_seconds: int = 30,
    ) -> None:
        self._jwks = jwks
        self._issuer = issuer
        self._audience = audience
        self._leeway = leeway_seconds

    def verify(self, token: str) -> IdentityClaims:
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthError("malformed token")
        header_b64, body_b64, sig_b64 = parts
        try:
            header = json.loads(_b64url_decode(header_b64))
        except (ValueError, json.JSONDecodeError) as exc:
            raise AuthError("malformed header") from exc
        if header.get("alg") != "RS256":
            raise AuthError("unsupported alg")
        kid = header.get("kid")
        if not isinstance(kid, str) or not kid:
            raise AuthError("missing kid")
        public_key = self._jwks.get(kid)
        signing_input = f"{header_b64}.{body_b64}".encode()
        try:
            signature = _b64url_decode(sig_b64)
        except ValueError as exc:
            raise AuthError("malformed signature") from exc
        try:
            public_key.verify(
                signature,
                signing_input,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except InvalidSignature as exc:
            raise AuthError("bad signature") from exc
        try:
            payload = json.loads(_b64url_decode(body_b64))
        except (ValueError, json.JSONDecodeError) as exc:
            raise AuthError("malformed body") from exc
        now = int(time.time())
        exp = int(payload.get("exp", 0))
        if exp and now > exp + self._leeway:
            raise AuthError("token expired")
        if payload.get("iss") != self._issuer:
            raise AuthError("issuer mismatch")
        aud = payload.get("aud")
        if isinstance(aud, list):
            if self._audience not in aud:
                raise AuthError("audience mismatch")
            payload["aud"] = self._audience
        elif aud != self._audience:
            raise AuthError("audience mismatch")
        keep = {"sub", "iss", "aud", "exp", "iat", "email", "scope"}
        filtered = {k: v for k, v in payload.items() if k in keep}
        try:
            return IdentityClaims(**filtered)  # type: ignore[arg-type]
        except Exception as exc:
            raise AuthError(f"invalid claims: {exc}") from exc


__all__ = [
    "AuthError",
    "HS256Verifier",
    "IdentityClaims",
    "JwksClient",
    "JwksFetcher",
    "RS256Verifier",
    "TokenVerifier",
    "has_scope",
]
