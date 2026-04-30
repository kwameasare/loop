"""Redis adapter for session memory.

Layout: each conversation owns one Redis hash at
``loop:session:{conversation_id}``. Keys inside the hash are session
attribute names; values are JSON-encoded. The whole hash carries a
24h TTL by default (SCHEMA.md §5); the TTL is refreshed on every
mutation so an active conversation never expires mid-turn.

We store each value as JSON so the type round-trips cleanly through
Redis bytes (which has no first-class type system).
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import redis.asyncio as redis_async

_DEFAULT_TTL_SECONDS = 24 * 60 * 60


def _key(conversation_id: UUID) -> str:
    return f"loop:session:{conversation_id}"


class RedisSessionMemoryStore:
    """``SessionMemoryStore`` impl over a redis.asyncio.Redis client."""

    def __init__(
        self,
        client: redis_async.Redis,
        *,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._client = client
        self._ttl = ttl_seconds

    async def get(self, *, conversation_id: UUID, key: str) -> Any | None:
        raw = await self._client.hget(_key(conversation_id), key)  # type: ignore[misc]
        if raw is None:
            return None
        return _decode(raw)

    async def set(self, *, conversation_id: UUID, key: str, value: Any) -> None:
        k = _key(conversation_id)
        encoded = json.dumps(value, default=str)
        # Pipeline so the TTL refresh and write are atomic against a
        # concurrent ``clear``.
        async with self._client.pipeline(transaction=True) as pipe:
            await pipe.hset(k, key, encoded)  # type: ignore[misc]
            await pipe.expire(k, self._ttl)
            await pipe.execute()

    async def delete(self, *, conversation_id: UUID, key: str) -> bool:
        removed = await self._client.hdel(_key(conversation_id), key)  # type: ignore[misc]
        return int(removed) > 0

    async def all(self, *, conversation_id: UUID) -> dict[str, Any]:
        raw = await self._client.hgetall(_key(conversation_id))  # type: ignore[misc]
        out: dict[str, Any] = {}
        for k, v in (raw or {}).items():
            key_s = k.decode() if isinstance(k, bytes) else k
            out[key_s] = _decode(v)
        return out

    async def clear(self, *, conversation_id: UUID) -> None:
        await self._client.delete(_key(conversation_id))


def _decode(raw: Any) -> Any:
    if isinstance(raw, bytes):
        raw = raw.decode()
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return raw


__all__ = ["RedisSessionMemoryStore"]
