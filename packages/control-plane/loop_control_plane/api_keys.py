"""API key issuance + verification.

Plaintext is shown to the caller exactly once at creation; the store
keeps only a hash. Verification uses the visible `prefix` to look up
the row in O(1) and then constant-time compares the SHA-256 hash.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

KEY_PREFIX = "loop_sk_"
PREFIX_LEN = 12  # length of the visible prefix portion (after KEY_PREFIX)
SECRET_BYTES = 32


class ApiKey(BaseModel):
    """Stored representation. ``hash`` is SHA-256 of the plaintext key."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: UUID
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=64)
    prefix: str = Field(min_length=PREFIX_LEN, max_length=PREFIX_LEN)
    hash: str = Field(min_length=64, max_length=64)
    created_at: datetime
    created_by: str = Field(min_length=1)
    revoked_at: datetime | None = None


class IssuedApiKey(BaseModel):
    """Returned to the caller once at creation. Plaintext lives here."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    record: ApiKey
    plaintext: str = Field(min_length=1)


class ApiKeyError(ValueError):
    """Raised on invalid / revoked keys or duplicate prefixes."""


def _hash_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


class ApiKeyService:
    def __init__(self) -> None:
        self._by_id: dict[UUID, ApiKey] = {}
        self._by_prefix: dict[str, ApiKey] = {}
        self._lock = asyncio.Lock()

    async def issue(self, *, workspace_id: UUID, name: str, created_by: str) -> IssuedApiKey:
        secret = secrets.token_urlsafe(SECRET_BYTES)
        plaintext = f"{KEY_PREFIX}{secret}"
        prefix = secret[:PREFIX_LEN]
        async with self._lock:
            if prefix in self._by_prefix:  # vanishingly unlikely but possible
                raise ApiKeyError("prefix collision; retry")
            record = ApiKey(
                id=uuid4(),
                workspace_id=workspace_id,
                name=name,
                prefix=prefix,
                hash=_hash_key(plaintext),
                created_at=datetime.now(UTC),
                created_by=created_by,
            )
            self._by_id[record.id] = record
            self._by_prefix[prefix] = record
        return IssuedApiKey(record=record, plaintext=plaintext)

    async def verify(self, plaintext: str) -> ApiKey:
        if not plaintext.startswith(KEY_PREFIX):
            raise ApiKeyError("invalid key format")
        secret = plaintext[len(KEY_PREFIX) :]
        if len(secret) < PREFIX_LEN:
            raise ApiKeyError("invalid key format")
        prefix = secret[:PREFIX_LEN]
        async with self._lock:
            record = self._by_prefix.get(prefix)
        if record is None:
            raise ApiKeyError("unknown key")
        if record.revoked_at is not None:
            raise ApiKeyError("key revoked")
        if not hmac.compare_digest(record.hash, _hash_key(plaintext)):
            raise ApiKeyError("bad secret")
        return record

    async def revoke(self, *, key_id: UUID) -> ApiKey:
        async with self._lock:
            record = self._by_id.get(key_id)
            if record is None:
                raise ApiKeyError(f"unknown key: {key_id}")
            if record.revoked_at is not None:
                return record
            updated = record.model_copy(update={"revoked_at": datetime.now(UTC)})
            self._by_id[key_id] = updated
            self._by_prefix[record.prefix] = updated
            return updated

    async def list_for_workspace(self, workspace_id: UUID) -> list[ApiKey]:
        async with self._lock:
            return [k for k in self._by_id.values() if k.workspace_id == workspace_id]


__all__ = [
    "KEY_PREFIX",
    "ApiKey",
    "ApiKeyError",
    "ApiKeyService",
    "IssuedApiKey",
    "PostgresApiKeyService",
]


# ---------------------------------------------------------------------------
# Postgres-backed service [P0.2]
# ---------------------------------------------------------------------------


class PostgresApiKeyService:
    """Postgres-backed API-key store — drop-in for :class:`ApiKeyService`.

    Same async surface (``issue / verify / revoke /
    list_for_workspace``), same :class:`ApiKey` / :class:`IssuedApiKey`
    return types, same :class:`ApiKeyError` failure mode.

    Schema lives in ``cp_0001_initial`` (api_keys) +
    ``cp_0011_api_keys_align`` (hash → TEXT, created_by → TEXT,
    drop RLS to allow verify-by-prefix lookups, add unique index on
    prefix).

    The prefix-uniqueness guarantee from cp_0011 means
    :meth:`verify`'s lookup is O(log n) on an index-backed scan and
    cannot ambiguously match two keys.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @classmethod
    def from_url(
        cls, database_url: str, *, echo: bool = False
    ) -> PostgresApiKeyService:
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(
            database_url,
            echo=echo,
            future=True,
            pool_pre_ping=True,
        )
        return cls(engine)

    async def issue(
        self, *, workspace_id: UUID, name: str, created_by: str
    ) -> IssuedApiKey:
        from sqlalchemy import text
        from sqlalchemy.exc import IntegrityError

        # Mint plaintext + hash exactly like the in-memory impl so
        # downstream callers (verify) round-trip identically.
        secret = secrets.token_urlsafe(SECRET_BYTES)
        plaintext = f"{KEY_PREFIX}{secret}"
        prefix = secret[:PREFIX_LEN]
        new_id = uuid4()
        now = datetime.now(UTC)
        hashed = _hash_key(plaintext)

        try:
            async with self._engine.begin() as conn:
                await conn.execute(
                    text(
                        """
                        INSERT INTO api_keys (
                            id, workspace_id, name, prefix, hash,
                            created_at, created_by
                        ) VALUES (
                            :id, :workspace_id, :name, :prefix, :hash,
                            :created_at, :created_by
                        )
                        """
                    ),
                    {
                        "id": new_id,
                        "workspace_id": workspace_id,
                        "name": name,
                        "prefix": prefix,
                        "hash": hashed,
                        "created_at": now,
                        "created_by": created_by,
                    },
                )
        except IntegrityError as exc:
            # Globally-unique prefix collision (vanishingly unlikely
            # with 12 chars of token_urlsafe entropy) OR FK rejection
            # for an unknown workspace_id. Either way the in-memory
            # impl raises ApiKeyError("prefix collision; retry").
            raise ApiKeyError("prefix collision; retry") from exc

        record = ApiKey(
            id=new_id,
            workspace_id=workspace_id,
            name=name,
            prefix=prefix,
            hash=hashed,
            created_at=now,
            created_by=created_by,
        )
        return IssuedApiKey(record=record, plaintext=plaintext)

    async def verify(self, plaintext: str) -> ApiKey:
        from sqlalchemy import text

        if not plaintext.startswith(KEY_PREFIX):
            raise ApiKeyError("invalid key format")
        secret = plaintext[len(KEY_PREFIX) :]
        if len(secret) < PREFIX_LEN:
            raise ApiKeyError("invalid key format")
        prefix = secret[:PREFIX_LEN]

        async with self._engine.connect() as conn:
            row = (
                await conn.execute(
                    text(
                        """
                        SELECT id, workspace_id, name, prefix, hash,
                               created_at, created_by, revoked_at
                          FROM api_keys
                         WHERE prefix = :prefix
                        """
                    ),
                    {"prefix": prefix},
                )
            ).first()
        if row is None:
            raise ApiKeyError("unknown key")
        if row.revoked_at is not None:
            raise ApiKeyError("key revoked")
        if not hmac.compare_digest(row.hash, _hash_key(plaintext)):
            raise ApiKeyError("bad secret")
        return _row_to_api_key(row)

    async def revoke(self, *, key_id: UUID) -> ApiKey:
        from sqlalchemy import text

        async with self._engine.begin() as conn:
            row = (
                await conn.execute(
                    text(
                        """
                        SELECT id, workspace_id, name, prefix, hash,
                               created_at, created_by, revoked_at
                          FROM api_keys
                         WHERE id = :id
                           FOR UPDATE
                        """
                    ),
                    {"id": key_id},
                )
            ).first()
            if row is None:
                raise ApiKeyError(f"unknown key: {key_id}")
            if row.revoked_at is not None:
                # Idempotent — return the existing snapshot, don't
                # bump revoked_at again. Matches the in-memory impl.
                return _row_to_api_key(row)
            now = datetime.now(UTC)
            await conn.execute(
                text(
                    "UPDATE api_keys SET revoked_at = :now WHERE id = :id"
                ),
                {"now": now, "id": key_id},
            )
        return _row_to_api_key(row).model_copy(update={"revoked_at": now})

    async def list_for_workspace(self, workspace_id: UUID) -> list[ApiKey]:
        from sqlalchemy import text

        async with self._engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        """
                        SELECT id, workspace_id, name, prefix, hash,
                               created_at, created_by, revoked_at
                          FROM api_keys
                         WHERE workspace_id = :workspace_id
                         ORDER BY created_at ASC
                        """
                    ),
                    {"workspace_id": workspace_id},
                )
            ).all()
        return [_row_to_api_key(row) for row in rows]


def _row_to_api_key(row: object) -> ApiKey:
    return ApiKey(
        id=row.id,  # type: ignore[attr-defined]
        workspace_id=row.workspace_id,  # type: ignore[attr-defined]
        name=row.name,  # type: ignore[attr-defined]
        prefix=row.prefix,  # type: ignore[attr-defined]
        hash=row.hash,  # type: ignore[attr-defined]
        created_at=row.created_at,  # type: ignore[attr-defined]
        created_by=row.created_by,  # type: ignore[attr-defined]
        revoked_at=row.revoked_at,  # type: ignore[attr-defined]
    )
