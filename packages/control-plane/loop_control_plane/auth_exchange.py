"""Auth0 → Loop PASETO exchange (S105).

The cp-api ``POST /v1/auth/exchange`` route accepts a verified Auth0
JWT (already validated by the JwtValidator from S104) and returns a
short-lived Loop PASETO + a refresh token. The refresh token is
opaque — it is a hash-stored row in the database and is *not* the
same shape as the access token.

This module is the service-layer surface that the route handler
calls. The HTTP/FastAPI shim is intentionally separate so we can
unit-test the swap without spinning the framework.
"""

from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Protocol

from loop_control_plane.jwks import JwtClaims
from loop_control_plane.paseto import encode_local

__all__ = [
    "REFRESH_FAMILY_TTL_MS",
    "REFRESH_TTL_MS",
    "AuthExchange",
    "AuthExchangeError",
    "ExchangeResult",
    "RefreshTokenRecord",
    "RefreshTokenStore",
    "UnknownIdpUser",
]

ACCESS_TTL_MS = 60 * 60 * 1000
REFRESH_TTL_MS = 30 * 24 * 60 * 60 * 1000
REFRESH_FAMILY_TTL_MS = 90 * 24 * 60 * 60 * 1000


class AuthExchangeError(ValueError):
    """Raised when an exchange cannot be completed."""


class UnknownIdpUser(AuthExchangeError):  # noqa: N818  -- domain-named exception, intentional
    """The Auth0 ``sub`` claim does not map to a Loop user row."""


@dataclass(frozen=True)
class ExchangeResult:
    access_token: str
    """Loop PASETO bearer token used on cp-api/dp-runtime requests."""
    refresh_token: str
    """Opaque refresh token; only the SHA-256 hash is stored server-side."""
    access_expires_at_ms: int
    refresh_expires_at_ms: int


@dataclass(frozen=True)
class RefreshTokenRecord:
    user_sub: str
    expires_at_ms: int
    family_id: str
    family_expires_at_ms: int
    revoked_at_ms: int | None = None


class RefreshTokenStore(Protocol):
    """Persistence shim: stores hashed refresh tokens with TTL."""

    async def put(
        self,
        *,
        user_sub: str,
        token_hash: str,
        expires_at_ms: int,
        family_id: str,
        family_expires_at_ms: int,
    ) -> None: ...

    async def revoke(self, token_hash: str) -> None: ...

    async def revoke_family(self, family_id: str) -> None: ...

    def lookup(self, token_hash: str) -> RefreshTokenRecord | None: ...


# Mapper: idp ``sub`` → loop ``user_id`` (UUID-string). Returns None
# when the IdP user has not yet been provisioned.
IdpUserMapper = Callable[[str], Awaitable[str | None]]


@dataclass(frozen=True)
class AuthExchange:
    paseto_key: bytes
    refresh_store: RefreshTokenStore
    user_mapper: IdpUserMapper
    expected_audience: str
    access_ttl_ms: int = ACCESS_TTL_MS
    refresh_ttl_ms: int = REFRESH_TTL_MS
    refresh_family_ttl_ms: int = REFRESH_FAMILY_TTL_MS

    async def exchange(self, *, claims: JwtClaims, now_ms: int) -> ExchangeResult:
        # Audience pinning is the *outer* JwtValidator's job, but we
        # double-check here because exchange is the trust-boundary.
        if self.expected_audience not in claims.aud:
            raise AuthExchangeError(
                f"audience mismatch: got {claims.aud!r}, expected {self.expected_audience!r} present"
            )
        loop_user_id = await self.user_mapper(claims.sub)
        if loop_user_id is None:
            raise UnknownIdpUser(claims.sub)

        access_token = encode_local(
            {"sub": loop_user_id, "iss": "loop", "aud": self.expected_audience},
            key=self.paseto_key,
            now_ms=now_ms,
            expires_in_ms=self.access_ttl_ms,
        )
        refresh_token = secrets.token_urlsafe(32)
        refresh_hash = sha256(refresh_token.encode("ascii")).hexdigest()
        family_id = secrets.token_urlsafe(24)
        family_expires_at = now_ms + self.refresh_family_ttl_ms
        refresh_expires_at = min(now_ms + self.refresh_ttl_ms, family_expires_at)
        await self.refresh_store.put(
            user_sub=loop_user_id,
            token_hash=refresh_hash,
            expires_at_ms=refresh_expires_at,
            family_id=family_id,
            family_expires_at_ms=family_expires_at,
        )
        return ExchangeResult(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_at_ms=now_ms + self.access_ttl_ms,
            refresh_expires_at_ms=refresh_expires_at,
        )


class InMemoryRefreshTokenStore:
    """Test double; production wiring uses a Postgres ``refresh_tokens`` row."""

    def __init__(self) -> None:
        self._rows: dict[str, RefreshTokenRecord] = {}

    async def put(
        self,
        *,
        user_sub: str,
        token_hash: str,
        expires_at_ms: int,
        family_id: str,
        family_expires_at_ms: int,
    ) -> None:
        self._rows[token_hash] = RefreshTokenRecord(
            user_sub=user_sub,
            expires_at_ms=expires_at_ms,
            family_id=family_id,
            family_expires_at_ms=family_expires_at_ms,
        )

    async def revoke(self, token_hash: str) -> None:
        record = self._rows.get(token_hash)
        if record is not None and record.revoked_at_ms is None:
            self._rows[token_hash] = replace(record, revoked_at_ms=0)

    async def revoke_family(self, family_id: str) -> None:
        for token_hash, record in tuple(self._rows.items()):
            if record.family_id == family_id and record.revoked_at_ms is None:
                self._rows[token_hash] = replace(record, revoked_at_ms=0)

    def lookup(self, token_hash: str) -> RefreshTokenRecord | None:
        return self._rows.get(token_hash)
