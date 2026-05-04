"""Client tests: alias resolution, provider routing, idempotency replay,
cross-workspace isolation."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import fakeredis.aioredis
import pytest
from loop_gateway import GatewayDelta, GatewayDone, GatewayRequest, Usage
from loop_gateway.client import GatewayClient
from loop_gateway.idempotency_redis import RedisIdempotencyCache
from loop_gateway.providers import AnthropicProvider, OpenAIProvider
from loop_gateway.types import GatewayMessage


def _msgs() -> tuple[GatewayMessage, ...]:
    return (GatewayMessage(role="user", content="hi"),)


def _openai_canned_lines(label: str) -> list[str]:
    return [
        f'data: {{"choices":[{{"delta":{{"content":"{label}"}}}}]}}',
        'data: {"usage":{"prompt_tokens":1000,"completion_tokens":1000}}',
        "data: [DONE]",
    ]


def _anthropic_canned_lines(label: str) -> list[str]:
    return [
        "event: content_block_delta",
        f'data: {{"delta":{{"text":"{label}"}}}}',
        "",
        "event: message_delta",
        'data: {"usage":{"input_tokens":1,"output_tokens":1}}',
        "",
        "event: message_stop",
        "data: {}",
    ]


async def _wrap(lines: list[str]) -> AsyncIterator[str]:
    for line in lines:
        yield line


@pytest.mark.asyncio
async def test_alias_resolves_and_routes_to_correct_provider() -> None:
    # `cheap` -> claude-3-5-haiku per default aliases.yaml -> Anthropic.
    client = GatewayClient(
        providers=[
            OpenAIProvider(transport=lambda _r: _wrap(_openai_canned_lines("OPEN"))),
            AnthropicProvider(transport=lambda _r: _wrap(_anthropic_canned_lines("ANTH"))),
        ]
    )
    req = GatewayRequest(request_id="r1", workspace_id="ws-a", model="cheap", messages=_msgs())
    events = [e async for e in client.stream(req)]
    deltas = [e.text for e in events if isinstance(e, GatewayDelta)]
    assert deltas == ["ANTH"], "cheap alias must hit Anthropic"


@pytest.mark.asyncio
async def test_idempotency_replay_returns_recorded_events() -> None:
    call_count = 0

    def transport_factory():
        async def transport(_req: GatewayRequest) -> AsyncIterator[str]:
            nonlocal call_count
            call_count += 1
            for line in _openai_canned_lines("once"):
                yield line

        return transport

    client = GatewayClient(providers=[OpenAIProvider(transport=transport_factory())])
    req = GatewayRequest(
        request_id="r-dup", workspace_id="ws-a", model="gpt-4o-mini", messages=_msgs()
    )
    first = [e async for e in client.stream(req)]
    second = [e async for e in client.stream(req)]
    assert call_count == 1, "duplicate request_id must not hit upstream twice"
    assert first == second


@pytest.mark.asyncio
async def test_redis_idempotency_cache_claim_is_atomic_and_has_ttl() -> None:
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    cache = RedisIdempotencyCache(redis, ttl_seconds=1)

    assert await cache.claim("ws-a", "r-1") is True
    assert await cache.claim("ws-a", "r-1") is False
    await cache.set("ws-a", "r-1", [GatewayDelta(text="cached")])
    assert await cache.get("ws-a", "r-1") == [GatewayDelta(text="cached")]

    await asyncio.sleep(1.1)
    assert await cache.get("ws-a", "r-1") is None
    assert await cache.claim("ws-a", "r-1") is True


@pytest.mark.asyncio
async def test_redis_idempotency_cache_dedupes_across_gateway_clients() -> None:
    server = fakeredis.FakeServer()
    redis_a = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    redis_b = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    upstream_entered = asyncio.Event()
    call_count = 0

    async def transport(_req: GatewayRequest) -> AsyncIterator[str]:
        nonlocal call_count
        call_count += 1
        upstream_entered.set()
        await asyncio.sleep(0.05)
        for line in _openai_canned_lines("once"):
            yield line

    client_a = GatewayClient(
        providers=[OpenAIProvider(transport=transport)],
        idempotency_cache=RedisIdempotencyCache(redis_a, ttl_seconds=5),
    )
    client_b = GatewayClient(
        providers=[OpenAIProvider(transport=transport)],
        idempotency_cache=RedisIdempotencyCache(redis_b, ttl_seconds=5),
    )
    req = GatewayRequest(
        request_id="r-cross-pod",
        workspace_id="ws-a",
        model="gpt-4o-mini",
        messages=_msgs(),
    )

    task_a = asyncio.create_task(_collect(client_a, req))
    await upstream_entered.wait()
    task_b = asyncio.create_task(_collect(client_b, req))
    first, second = await asyncio.gather(task_a, task_b)

    assert call_count == 1
    assert first == second


@pytest.mark.asyncio
async def test_idempotency_cache_does_not_leak_across_workspaces() -> None:
    """Cross-workspace cache hits would be a P0 isolation bug (SECURITY.md)."""
    seen_workspaces: list[str] = []

    def transport(_req: GatewayRequest) -> AsyncIterator[str]:
        seen_workspaces.append(_req.workspace_id)
        return _wrap(_openai_canned_lines("ok"))

    client = GatewayClient(providers=[OpenAIProvider(transport=transport)])
    req_a = GatewayRequest(
        request_id="same-id", workspace_id="ws-a", model="gpt-4o-mini", messages=_msgs()
    )
    req_b = GatewayRequest(
        request_id="same-id", workspace_id="ws-b", model="gpt-4o-mini", messages=_msgs()
    )
    [e async for e in client.stream(req_a)]
    [e async for e in client.stream(req_b)]
    # Same request_id but different workspaces -- both must hit upstream.
    assert seen_workspaces == ["ws-a", "ws-b"]


@pytest.mark.asyncio
async def test_unknown_model_raises_lookup_error() -> None:
    client = GatewayClient(providers=[OpenAIProvider(transport=lambda _r: _wrap([]))])
    req = GatewayRequest(
        request_id="r1",
        workspace_id="ws-a",
        model="claude-3-5-sonnet",
        messages=_msgs(),
    )
    with pytest.raises(LookupError):
        async for _ in client.stream(req):
            pass


@pytest.mark.asyncio
async def test_done_event_carries_usage_and_cost() -> None:
    client = GatewayClient(
        providers=[OpenAIProvider(transport=lambda _r: _wrap(_openai_canned_lines("hi")))]
    )
    req = GatewayRequest(
        request_id="r1", workspace_id="ws-a", model="gpt-4o-mini", messages=_msgs()
    )
    events = [e async for e in client.stream(req)]
    done = [e for e in events if isinstance(e, GatewayDone)]
    assert len(done) == 1
    assert done[0].usage == Usage(input_tokens=1000, output_tokens=1000)
    assert done[0].cost_usd > 0


async def _collect(client: GatewayClient, req: GatewayRequest):
    return [event async for event in client.stream(req)]
