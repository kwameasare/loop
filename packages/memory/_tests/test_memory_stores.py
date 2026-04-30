"""Behavioural tests for the in-memory + Redis fake stores.

The Postgres adapter is exercised by the integration suite (S007 +
the memory smoke test scheduled for S016); here we cover the
contract surface every implementation has to honour.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from loop_memory import (
    InMemorySessionMemoryStore,
    InMemoryUserMemoryStore,
    MemoryNotFoundError,
    MemoryScope,
    RedisSessionMemoryStore,
)


@pytest.mark.asyncio
async def test_user_memory_set_then_get_round_trips_value() -> None:
    store = InMemoryUserMemoryStore()
    ws, ag = uuid4(), uuid4()
    entry = await store.set_user(
        workspace_id=ws,
        agent_id=ag,
        user_id="u-1",
        key="lang",
        value={"primary": "en", "secondary": "fr"},
    )
    assert entry.scope is MemoryScope.USER
    assert entry.user_id == "u-1"

    got = await store.get_user(workspace_id=ws, agent_id=ag, user_id="u-1", key="lang")
    assert got.value == {"primary": "en", "secondary": "fr"}
    assert got.workspace_id == ws


@pytest.mark.asyncio
async def test_user_memory_get_missing_raises_not_found_get_or_none_returns_none() -> None:
    store = InMemoryUserMemoryStore()
    ws, ag = uuid4(), uuid4()
    with pytest.raises(MemoryNotFoundError):
        await store.get_user(workspace_id=ws, agent_id=ag, user_id="u", key="x")
    got = await store.get_user_or_none(workspace_id=ws, agent_id=ag, user_id="u", key="x")
    assert got is None


@pytest.mark.asyncio
async def test_user_memory_isolated_per_tenant() -> None:
    """Critical: same (agent, user, key) in two workspaces never collide."""

    store = InMemoryUserMemoryStore()
    ws_a, ws_b, ag = uuid4(), uuid4(), uuid4()
    await store.set_user(workspace_id=ws_a, agent_id=ag, user_id="u", key="k", value="A")
    await store.set_user(workspace_id=ws_b, agent_id=ag, user_id="u", key="k", value="B")
    assert (await store.get_user(workspace_id=ws_a, agent_id=ag, user_id="u", key="k")).value == "A"
    assert (await store.get_user(workspace_id=ws_b, agent_id=ag, user_id="u", key="k")).value == "B"


@pytest.mark.asyncio
async def test_user_memory_list_returns_all_keys_for_user_only() -> None:
    store = InMemoryUserMemoryStore()
    ws, ag = uuid4(), uuid4()
    await store.set_user(workspace_id=ws, agent_id=ag, user_id="u-1", key="a", value=1)
    await store.set_user(workspace_id=ws, agent_id=ag, user_id="u-1", key="b", value=2)
    await store.set_user(workspace_id=ws, agent_id=ag, user_id="u-2", key="a", value=99)
    entries = await store.list_user(workspace_id=ws, agent_id=ag, user_id="u-1")
    keys = sorted(e.key for e in entries)
    assert keys == ["a", "b"]


@pytest.mark.asyncio
async def test_user_memory_delete_returns_true_only_when_present() -> None:
    store = InMemoryUserMemoryStore()
    ws, ag = uuid4(), uuid4()
    await store.set_user(workspace_id=ws, agent_id=ag, user_id="u", key="k", value=1)
    assert await store.delete_user(workspace_id=ws, agent_id=ag, user_id="u", key="k")
    assert not await store.delete_user(workspace_id=ws, agent_id=ag, user_id="u", key="k")


@pytest.mark.asyncio
async def test_bot_memory_round_trip_and_no_user_id_required() -> None:
    store = InMemoryUserMemoryStore()
    ws, ag = uuid4(), uuid4()
    entry = await store.set_bot(
        workspace_id=ws, agent_id=ag, key="persona", value={"tone": "formal"}
    )
    assert entry.scope is MemoryScope.BOT
    assert entry.user_id is None
    got = await store.get_bot(workspace_id=ws, agent_id=ag, key="persona")
    assert got.value == {"tone": "formal"}


@pytest.mark.asyncio
async def test_user_memory_set_does_not_alias_callers_value() -> None:
    """Mutating the input dict after set must not change stored state."""

    store = InMemoryUserMemoryStore()
    ws, ag = uuid4(), uuid4()
    payload: dict[str, list[int]] = {"items": [1, 2]}
    await store.set_user(workspace_id=ws, agent_id=ag, user_id="u", key="cart", value=payload)
    payload["items"].append(99)
    got = await store.get_user(workspace_id=ws, agent_id=ag, user_id="u", key="cart")
    assert got.value == {"items": [1, 2]}


@pytest.mark.asyncio
async def test_session_memory_get_set_clear() -> None:
    store = InMemorySessionMemoryStore()
    conv = uuid4()
    assert await store.get(conversation_id=conv, key="step") is None
    await store.set(conversation_id=conv, key="step", value=2)
    assert await store.get(conversation_id=conv, key="step") == 2
    await store.set(conversation_id=conv, key="cart", value=[1, 2])
    assert await store.all(conversation_id=conv) == {"step": 2, "cart": [1, 2]}
    await store.clear(conversation_id=conv)
    assert await store.all(conversation_id=conv) == {}


@pytest.mark.asyncio
async def test_session_memory_isolated_per_conversation() -> None:
    store = InMemorySessionMemoryStore()
    a, b = uuid4(), uuid4()
    await store.set(conversation_id=a, key="x", value=1)
    await store.set(conversation_id=b, key="x", value=2)
    assert await store.get(conversation_id=a, key="x") == 1
    assert await store.get(conversation_id=b, key="x") == 2


# ---------------------------------------------------------------------------
# Redis adapter -- exercised against fakeredis when available, otherwise via
# a tiny in-process double that satisfies the methods we call.
# ---------------------------------------------------------------------------


class _FakeRedis:
    """Minimal redis.asyncio stand-in supporting the calls we make."""

    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}
        self.ttls: dict[str, int] = {}

    async def hset(self, key: str, field: str, value: str) -> int:
        self.hashes.setdefault(key, {})[field] = value
        return 1

    async def hget(self, key: str, field: str) -> bytes | None:
        v = self.hashes.get(key, {}).get(field)
        return v.encode() if v is not None else None

    async def hdel(self, key: str, field: str) -> int:
        h = self.hashes.get(key, {})
        return 1 if h.pop(field, None) is not None else 0

    async def hgetall(self, key: str) -> dict[bytes, bytes]:
        h = self.hashes.get(key, {})
        return {k.encode(): v.encode() for k, v in h.items()}

    async def expire(self, key: str, seconds: int) -> bool:
        self.ttls[key] = seconds
        return True

    async def delete(self, key: str) -> int:
        existed = key in self.hashes
        self.hashes.pop(key, None)
        self.ttls.pop(key, None)
        return 1 if existed else 0

    def pipeline(self, *, transaction: bool = True) -> _FakePipeline:
        return _FakePipeline(self)


class _FakePipeline:
    def __init__(self, parent: _FakeRedis) -> None:
        self._parent = parent
        self._ops: list[tuple[str, tuple[object, ...]]] = []

    async def __aenter__(self) -> _FakePipeline:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None

    async def hset(self, key: str, field: str, value: str) -> _FakePipeline:
        self._ops.append(("hset", (key, field, value)))
        return self

    async def expire(self, key: str, seconds: int) -> _FakePipeline:
        self._ops.append(("expire", (key, seconds)))
        return self

    async def execute(self) -> list[object]:
        results: list[object] = []
        for name, args in self._ops:
            method = getattr(self._parent, name)
            results.append(await method(*args))
        self._ops.clear()
        return results


@pytest.mark.asyncio
async def test_redis_session_memory_round_trip_and_ttl_refresh() -> None:
    fake = _FakeRedis()
    store = RedisSessionMemoryStore(fake, ttl_seconds=60)  # type: ignore[arg-type]
    conv = uuid4()

    await store.set(conversation_id=conv, key="step", value={"n": 3})
    assert fake.ttls[f"loop:session:{conv}"] == 60
    assert await store.get(conversation_id=conv, key="step") == {"n": 3}

    # Refreshing TTL on every set: change ttl seconds via re-construction
    fake.ttls.clear()
    store2 = RedisSessionMemoryStore(fake, ttl_seconds=120)  # type: ignore[arg-type]
    await store2.set(conversation_id=conv, key="step", value=4)
    assert fake.ttls[f"loop:session:{conv}"] == 120

    everything = await store.all(conversation_id=conv)
    assert everything == {"step": 4}

    assert await store.delete(conversation_id=conv, key="step")
    assert not await store.delete(conversation_id=conv, key="step")

    await store.set(conversation_id=conv, key="x", value=1)
    await store.clear(conversation_id=conv)
    assert await store.all(conversation_id=conv) == {}


def test_redis_session_memory_rejects_non_positive_ttl() -> None:
    fake = _FakeRedis()
    with pytest.raises(ValueError):
        RedisSessionMemoryStore(fake, ttl_seconds=0)  # type: ignore[arg-type]
