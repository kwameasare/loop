"""Auth: minimal JWT (HS256) verifier with Auth0-shaped claims.

Production wiring will swap the in-memory key for a JWKS-backed RS256
verifier behind the same `TokenVerifier` Protocol; nothing in the
control-plane API layer should depend on the verification mechanics.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Sequence
from typing import Protocol

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

    Real deployments use `Auth0RS256Verifier` (TBD) -- this exists so
    the rest of the control plane can build against `TokenVerifier`
    without standing up Auth0 first.
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


__all__ = [
    "AuthError",
    "HS256Verifier",
    "IdentityClaims",
    "TokenVerifier",
    "has_scope",
]
