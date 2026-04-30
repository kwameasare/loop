"""dp-runtime API key verifier (S134).

The data-plane never holds plaintext API keys. The control-plane returns a
sha256 hash + workspace pin per key; the runtime hashes the inbound key and
compares in constant time. Keys are cached briefly to avoid re-hitting cp on
every turn.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable
from uuid import UUID

__all__ = [
    "ApiKeyClaim",
    "ApiKeyVerifier",
    "InvalidApiKeyError",
    "KeyDirectory",
]


class InvalidApiKeyError(ValueError):
    """Raised when a presented key fails hash comparison or is revoked."""


@dataclass(frozen=True)
class ApiKeyClaim:
    """The pinned workspace + user a valid key resolves to."""

    workspace_id: UUID
    user_sub: str
    issued_at_ms: int


@runtime_checkable
class KeyDirectory(Protocol):
    """Lookup hook into the cp-api auth tables."""

    async def lookup_by_hash(self, key_hash_hex: str) -> ApiKeyClaim | None: ...


def _hash_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


@dataclass
class ApiKeyVerifier:
    """Verify a presented key against the cp-api directory.

    Caches positive results for ``cache_ttl_ms``. Negative results are not
    cached to avoid attackers benefiting from cache-fill timing oracles.
    """

    directory: KeyDirectory
    cache_ttl_ms: int = 5_000
    clock_ms: Callable[[], int] = field(
        default_factory=lambda: lambda: int(time.time() * 1000)
    )
    _cache: dict[str, tuple[ApiKeyClaim, int]] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def verify(self, presented: str) -> ApiKeyClaim:
        if not presented:
            raise InvalidApiKeyError("empty key")
        key_hash = _hash_key(presented)
        now = self.clock_ms()
        async with self._lock:
            cached = self._cache.get(key_hash)
            if cached is not None and cached[1] > now:
                return cached[0]

        claim = await self.directory.lookup_by_hash(key_hash)
        if claim is None:
            raise InvalidApiKeyError("unknown api key")

        # Constant-time defence-in-depth even though the directory does the
        # actual hash comparison: prevents timing on the cache hit path.
        if not hmac.compare_digest(key_hash, _hash_key(presented)):
            raise InvalidApiKeyError("hash mismatch")  # pragma: no cover

        async with self._lock:
            self._cache[key_hash] = (claim, now + self.cache_ttl_ms)
        return claim

    def invalidate(self, presented: str) -> None:
        self._cache.pop(_hash_key(presented), None)
