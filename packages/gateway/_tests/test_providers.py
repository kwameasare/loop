"""Provider streaming tests with deterministic in-memory transports."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from loop_gateway.providers import AnthropicProvider, OpenAIProvider
from loop_gateway.types import (
    GatewayDelta,
    GatewayDone,
    GatewayError,
    GatewayMessage,
    GatewayRequest,
)


def _request(model: str) -> GatewayRequest:
    return GatewayRequest(
        request_id="req-1",
        workspace_id="ws-1",
        model=model,
        messages=(GatewayMessage(role="user", content="hi"),),
    )


async def _from_lines(lines: list[str]) -> AsyncIterator[str]:
    for line in lines:
        yield line


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openai_streams_deltas_then_done() -> None:
    lines = [
        'data: {"choices":[{"delta":{"content":"Hello"}}]}',
        'data: {"choices":[{"delta":{"content":" world"}}]}',
        'data: {"usage":{"prompt_tokens":10000,"completion_tokens":2000}}',
        "data: [DONE]",
    ]
    provider = OpenAIProvider(transport=lambda _req: _wrap(lines))
    events = [e async for e in provider.stream(_request("gpt-4o-mini"))]
    deltas = [e for e in events if isinstance(e, GatewayDelta)]
    assert [d.text for d in deltas] == ["Hello", " world"]
    done = events[-1]
    assert isinstance(done, GatewayDone)
    assert done.usage.input_tokens == 10000
    assert done.usage.output_tokens == 2000
    # cost > 0 and markup applied (we don't pin the exact penny here -- cost.py owns that).
    assert done.cost_usd > 0
    assert done.cost_disclosed_markup_pct == 5.0


@pytest.mark.asyncio
async def test_openai_emits_error_on_bad_json() -> None:
    lines = ["data: {not json"]
    provider = OpenAIProvider(transport=lambda _req: _wrap(lines))
    events = [e async for e in provider.stream(_request("gpt-4o-mini"))]
    assert any(isinstance(e, GatewayError) for e in events)


def test_openai_supports_only_gpt_prefix() -> None:
    p = OpenAIProvider(transport=lambda _req: _wrap([]))
    assert p.supports("gpt-4o")
    assert not p.supports("claude-3-5-sonnet")


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_anthropic_streams_deltas_and_records_usage() -> None:
    lines = [
        "event: content_block_delta",
        'data: {"delta":{"text":"Hi"}}',
        "",
        "event: content_block_delta",
        'data: {"delta":{"text":" there"}}',
        "",
        "event: message_delta",
        'data: {"usage":{"input_tokens":7,"output_tokens":2}}',
        "",
        "event: message_stop",
        "data: {}",
    ]
    provider = AnthropicProvider(transport=lambda _req: _wrap(lines))
    events = [e async for e in provider.stream(_request("claude-3-5-haiku"))]
    deltas = [e for e in events if isinstance(e, GatewayDelta)]
    assert [d.text for d in deltas] == ["Hi", " there"]
    done = events[-1]
    assert isinstance(done, GatewayDone)
    assert done.usage.input_tokens == 7
    assert done.usage.output_tokens == 2


def test_anthropic_supports_only_claude_prefix() -> None:
    p = AnthropicProvider(transport=lambda _req: _wrap([]))
    assert p.supports("claude-3-5-sonnet")
    assert not p.supports("gpt-4o")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


async def _wrap(lines: list[str]) -> AsyncIterator[str]:
    for line in lines:
        yield line
