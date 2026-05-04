"""Redis-backed gateway request-id idempotency cache."""

from __future__ import annotations

import json
from math import ceil
from typing import Any

from redis.asyncio import Redis

from loop_gateway.types import GatewayDelta, GatewayDone, GatewayError, GatewayEvent

_INFLIGHT = "__loop_gateway_inflight__"


class RedisIdempotencyCache:
    """Idempotency cache using Redis SET NX for multi-pod-safe claims."""

    def __init__(self, redis: Redis, *, ttl_seconds: float = 600.0, prefix: str = "loop:gw:idemp"):
        self._redis = redis
        self._ttl = max(1, ceil(ttl_seconds))
        self._prefix = prefix

    @classmethod
    def from_url(cls, url: str, *, ttl_seconds: float = 600.0) -> RedisIdempotencyCache:
        return cls(Redis.from_url(url, decode_responses=True), ttl_seconds=ttl_seconds)

    async def get(self, workspace_id: str, request_id: str) -> list[GatewayEvent] | None:
        raw = await self._redis.get(self._key(workspace_id, request_id))
        if raw is None or raw == _INFLIGHT:
            return None
        payload = json.loads(raw)
        events = payload.get("events", [])
        if not isinstance(events, list):
            return None
        return [_event_from_json(event) for event in events if isinstance(event, dict)]

    async def claim(self, workspace_id: str, request_id: str) -> bool:
        claimed = await self._redis.set(
            self._key(workspace_id, request_id),
            _INFLIGHT,
            ex=self._ttl,
            nx=True,
        )
        return bool(claimed)

    async def set(
        self,
        workspace_id: str,
        request_id: str,
        events: list[GatewayEvent],
    ) -> None:
        payload = {"events": [event.model_dump(mode="json") for event in events]}
        await self._redis.set(
            self._key(workspace_id, request_id),
            json.dumps(payload, separators=(",", ":")),
            ex=self._ttl,
        )

    def _key(self, workspace_id: str, request_id: str) -> str:
        return f"{self._prefix}:{workspace_id}:{request_id}"


def _event_from_json(payload: dict[str, Any]) -> GatewayEvent:
    kind = payload.get("kind")
    if kind == "delta":
        return GatewayDelta.model_validate(payload)
    if kind == "done":
        payload = payload | {"tool_calls": tuple(payload.get("tool_calls", ()))}
        return GatewayDone.model_validate(payload)
    if kind == "error":
        return GatewayError.model_validate(payload)
    raise ValueError(f"unknown gateway event kind: {kind!r}")


__all__ = ["RedisIdempotencyCache"]
