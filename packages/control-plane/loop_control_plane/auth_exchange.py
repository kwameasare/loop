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
from typing import TYPE_CHECKING, Protocol

from loop_control_plane.jwks import JwtClaims
from loop_control_plane.paseto import encode_local

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
    from sqlalchemy.ext.asyncio import AsyncEngine

__all__ = [
    "REFRESH_FAMILY_TTL_MS",
    "REFRESH_TTL_MS",
    "AuthExchange",
    "AuthExchangeError",
    "ExchangeResult",
    "InMemoryRefreshTokenStore",
    "PostgresRefreshTokenStore",
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


# ---------------------------------------------------------------------------
# Postgres-backed store [P0.2]
# ---------------------------------------------------------------------------


class PostgresRefreshTokenStore:
    """Postgres-backed refresh-token store — drop-in for InMemoryRefreshTokenStore.

    Schema lives in ``cp_0007_refresh_tokens``. The token_hash is the
    primary key, so :meth:`lookup` and :meth:`revoke` are O(1) PK
    operations.

    Mixed sync/async surface, mirroring the Protocol exactly:

    * :meth:`put`, :meth:`revoke`, :meth:`revoke_family` are async
      (called from the async route handlers; use an
      :class:`AsyncEngine` under the hood).
    * :meth:`lookup` is sync because the route handler at
      ``_routes_auth.auth_refresh`` calls it synchronously — the
      existing in-memory store made it sync, and the route's
      reuse-detection branching reads cleaner without intermediate
      ``await``\\ s. Uses a separate sync :class:`Engine` to avoid
      mixing sync calls into the async event loop's connection pool.

    Soft-delete revoke matches :class:`InMemoryRefreshTokenStore`:
    revoked rows stay in the table with ``revoked_at_ms`` set so the
    route can distinguish "never existed" (lookup → None) from
    "was once valid, now revoked" (lookup → record with
    ``revoked_at_ms``). The latter triggers family-wide revocation.
    """

    def __init__(self, async_engine: AsyncEngine, sync_engine: Engine) -> None:
        self._async_engine = async_engine
        self._sync_engine = sync_engine

    @classmethod
    def from_url(
        cls, database_url: str, *, echo: bool = False
    ) -> PostgresRefreshTokenStore:
        """Build a store from a SQLAlchemy URL.

        Constructs both an async and a sync engine off the same
        ``postgresql+psycopg://`` URL — psycopg3's dialect supports
        both.
        """
        from sqlalchemy import create_engine
        from sqlalchemy.ext.asyncio import create_async_engine

        async_engine = create_async_engine(
            database_url, echo=echo, future=True, pool_pre_ping=True
        )
        sync_engine = create_engine(
            database_url, echo=echo, future=True, pool_pre_ping=True
        )
        return cls(async_engine, sync_engine)

    async def put(
        self,
        *,
        user_sub: str,
        token_hash: str,
        expires_at_ms: int,
        family_id: str,
        family_expires_at_ms: int,
    ) -> None:
        from sqlalchemy import text

        async with self._async_engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO refresh_tokens (
                        token_hash, user_sub, expires_at_ms,
                        family_id, family_expires_at_ms
                    ) VALUES (
                        :token_hash, :user_sub, :expires_at_ms,
                        :family_id, :family_expires_at_ms
                    )
                    ON CONFLICT (token_hash) DO UPDATE
                       SET user_sub = EXCLUDED.user_sub,
                           expires_at_ms = EXCLUDED.expires_at_ms,
                           family_id = EXCLUDED.family_id,
                           family_expires_at_ms = EXCLUDED.family_expires_at_ms,
                           revoked_at_ms = NULL
                    """
                ),
                {
                    "token_hash": token_hash,
                    "user_sub": user_sub,
                    "expires_at_ms": expires_at_ms,
                    "family_id": family_id,
                    "family_expires_at_ms": family_expires_at_ms,
                },
            )

    async def revoke(self, token_hash: str) -> None:
        from sqlalchemy import text

        async with self._async_engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    UPDATE refresh_tokens
                       SET revoked_at_ms = 0
                     WHERE token_hash = :token_hash
                       AND revoked_at_ms IS NULL
                    """
                ),
                {"token_hash": token_hash},
            )

    async def revoke_family(self, family_id: str) -> None:
        from sqlalchemy import text

        async with self._async_engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    UPDATE refresh_tokens
                       SET revoked_at_ms = 0
                     WHERE family_id = :family_id
                       AND revoked_at_ms IS NULL
                    """
                ),
                {"family_id": family_id},
            )

    def lookup(self, token_hash: str) -> RefreshTokenRecord | None:
        from sqlalchemy import text

        with self._sync_engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT user_sub, expires_at_ms, family_id,
                           family_expires_at_ms, revoked_at_ms
                      FROM refresh_tokens
                     WHERE token_hash = :token_hash
                    """
                ),
                {"token_hash": token_hash},
            ).first()
        if row is None:
            return None
        return RefreshTokenRecord(
            user_sub=row.user_sub,
            expires_at_ms=row.expires_at_ms,
            family_id=row.family_id,
            family_expires_at_ms=row.family_expires_at_ms,
            revoked_at_ms=row.revoked_at_ms,
        )
