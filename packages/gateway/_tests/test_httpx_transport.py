"""Httpx transport + cassette replay tests for S906."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid4

import httpx
import pytest
import yaml
from loop_gateway.byo_keys import InMemoryWorkspaceKeyStore, Vendor, WorkspaceKeyResolver
from loop_gateway.providers import AnthropicProvider, OpenAIProvider
from loop_gateway.providers import httpx_transport as transport_module
from loop_gateway.types import (
    GatewayDelta,
    GatewayDone,
    GatewayError,
    GatewayMessage,
    GatewayRequest,
)

CASSETTES = Path(__file__).parent / "cassettes" / "gateway"


def _request(workspace_id: UUID, model: str) -> GatewayRequest:
    return GatewayRequest(
        request_id="req-s906",
        workspace_id=str(workspace_id),
        model=model,
        messages=(GatewayMessage(role="user", content="Say hello."),),
        temperature=0.0,
        max_output_tokens=16,
    )


def _cassette(name: str) -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load((CASSETTES / name).read_text()))


def _resolver(workspace_id: UUID, vendor: Vendor, api_key: str) -> WorkspaceKeyResolver:
    store = InMemoryWorkspaceKeyStore()
    store.set_vendor_key(workspace_id, vendor, api_key)
    return WorkspaceKeyResolver(store)


async def _client(
    cassette: dict[str, Any],
    seen: list[httpx.Request],
) -> httpx.AsyncClient:
    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        response = cast(dict[str, Any], cassette["response"])
        return httpx.Response(
            int(response["status_code"]),
            headers=cast(dict[str, str], response["headers"]),
            text=str(response["body"]),
        )

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_openai_provider_uses_httpx_transport_and_byo_key_cassette() -> None:
    workspace_id = uuid4()
    cassette = _cassette("openai_chat_completion.yaml")
    seen: list[httpx.Request] = []
    async with await _client(cassette, seen) as client:
        provider = OpenAIProvider(
            key_resolver=_resolver(workspace_id, Vendor.OPENAI, "workspace-openai-key"),
            client=client,
        )

        events = [event async for event in provider.stream(_request(workspace_id, "gpt-4o-mini"))]

    assert [event.text for event in events if isinstance(event, GatewayDelta)] == ["Hello"]
    assert isinstance(events[-1], GatewayDone)
    assert str(seen[0].url) == "https://api.openai.com/v1/chat/completions"
    assert seen[0].headers["authorization"] == "Bearer workspace-openai-key"
    payload = json.loads(seen[0].content)
    assert payload["stream"] is True
    assert payload["stream_options"] == {"include_usage": True}
    assert "workspace-openai-key" not in (CASSETTES / "openai_chat_completion.yaml").read_text()


@pytest.mark.asyncio
async def test_anthropic_provider_uses_httpx_transport_and_byo_key_cassette() -> None:
    workspace_id = uuid4()
    cassette = _cassette("anthropic_messages.yaml")
    seen: list[httpx.Request] = []
    async with await _client(cassette, seen) as client:
        provider = AnthropicProvider(
            key_resolver=_resolver(workspace_id, Vendor.ANTHROPIC, "workspace-anthropic-key"),
            client=client,
        )

        events = [
            event async for event in provider.stream(_request(workspace_id, "claude-3-5-haiku"))
        ]

    assert [event.text for event in events if isinstance(event, GatewayDelta)] == ["Hello"]
    assert isinstance(events[-1], GatewayDone)
    assert str(seen[0].url) == "https://api.anthropic.com/v1/messages"
    assert seen[0].headers["x-api-key"] == "workspace-anthropic-key"
    assert seen[0].headers["anthropic-version"] == "2023-06-01"
    assert json.loads(seen[0].content)["max_tokens"] == 16
    assert "workspace-anthropic-key" not in (CASSETTES / "anthropic_messages.yaml").read_text()


@pytest.mark.asyncio
async def test_httpx_transport_retries_provider_5xx_then_streams() -> None:
    workspace_id = uuid4()
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(500, text="provider down")
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            text='data: {"choices":[{"delta":{"content":"ok"}}]}\n'
            'data: {"usage":{"prompt_tokens":1,"completion_tokens":1}}\n'
            "data: [DONE]\n",
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAIProvider(
            key_resolver=_resolver(workspace_id, Vendor.OPENAI, "workspace-openai-key"),
            client=client,
            retry_backoff_seconds=0.0,
        )
        events = [event async for event in provider.stream(_request(workspace_id, "gpt-4o-mini"))]

    assert calls == 2
    assert [event.text for event in events if isinstance(event, GatewayDelta)] == ["ok"]


@pytest.mark.asyncio
async def test_httpx_transport_honors_retry_after_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    workspace_id = uuid4()
    calls = 0
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "5"}, text="slow down")
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            text='data: {"choices":[{"delta":{"content":"ok"}}]}\n'
            'data: {"usage":{"prompt_tokens":1,"completion_tokens":1}}\n'
            "data: [DONE]\n",
        )

    monkeypatch.setattr(transport_module, "sleep", fake_sleep)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAIProvider(
            key_resolver=_resolver(workspace_id, Vendor.OPENAI, "workspace-openai-key"),
            client=client,
        )
        events = [event async for event in provider.stream(_request(workspace_id, "gpt-4o-mini"))]

    assert calls == 2
    assert sleeps == [5.0]
    assert [event.text for event in events if isinstance(event, GatewayDelta)] == ["ok"]


@pytest.mark.asyncio
async def test_httpx_transport_uses_exponential_full_jitter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    calls = 0
    sleeps: list[float] = []
    jitter_windows: list[tuple[float, float]] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    def fake_uniform(low: float, high: float) -> float:
        jitter_windows.append((low, high))
        return high

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls <= 2:
            return httpx.Response(429, text="slow down")
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            text='data: {"choices":[{"delta":{"content":"ok"}}]}\n'
            'data: {"usage":{"prompt_tokens":1,"completion_tokens":1}}\n'
            "data: [DONE]\n",
        )

    monkeypatch.setattr(transport_module, "sleep", fake_sleep)
    monkeypatch.setattr(transport_module.random, "uniform", fake_uniform)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAIProvider(
            key_resolver=_resolver(workspace_id, Vendor.OPENAI, "workspace-openai-key"),
            client=client,
            max_retries=2,
            retry_backoff_seconds=0.1,
            max_retry_delay_ms=1_000,
        )
        events = [event async for event in provider.stream(_request(workspace_id, "gpt-4o-mini"))]

    assert calls == 3
    assert jitter_windows == [(0.0, 0.1), (0.0, 0.2)]
    assert sleeps == [0.1, 0.2]
    assert [event.text for event in events if isinstance(event, GatewayDelta)] == ["ok"]


def test_parse_retry_after_accepts_http_dates() -> None:
    now = datetime(2026, 5, 4, 16, 0, tzinfo=UTC)
    retry_at = now + timedelta(seconds=7)
    header = format_datetime(retry_at, usegmt=True)
    assert transport_module._parse_retry_after(header, now=now) == pytest.approx(7.0)


@pytest.mark.asyncio
async def test_httpx_transport_missing_key_yields_gateway_error() -> None:
    workspace_id = uuid4()
    provider = OpenAIProvider(key_resolver=WorkspaceKeyResolver(InMemoryWorkspaceKeyStore()))

    events = [event async for event in provider.stream(_request(workspace_id, "gpt-4o-mini"))]

    assert isinstance(events[0], GatewayError)
    assert events[0].code == "LOOP-GW-101"


@pytest.mark.asyncio
async def test_live_openai_or_anthropic_smoke_is_explicitly_gated() -> None:
    if os.getenv("LOOP_GATEWAY_LIVE_TESTS") != "1":
        pytest.skip("set LOOP_GATEWAY_LIVE_TESTS=1 to spend live provider quota")
    if os.getenv("LOOP_GATEWAY_OPENAI_API_KEY"):
        provider = OpenAIProvider()
        events = [event async for event in provider.stream(_request(uuid4(), "gpt-4o-mini"))]
    elif os.getenv("LOOP_GATEWAY_ANTHROPIC_API_KEY"):
        provider = AnthropicProvider()
        events = [event async for event in provider.stream(_request(uuid4(), "claude-3-5-haiku"))]
    else:
        pytest.skip("live gateway test requires an OpenAI or Anthropic key")
    assert any(isinstance(event, GatewayDelta | GatewayDone) for event in events)
