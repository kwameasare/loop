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
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

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
]
