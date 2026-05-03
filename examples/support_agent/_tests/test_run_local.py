"""Tests for ``examples/support_agent/run_local.py``.

Uses ``httpx.MockTransport`` to replay deterministic streaming responses
from OpenAI/Anthropic so the example's tool-call round-trip is covered
in CI without touching the network.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_run_local() -> Any:
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("run_local_mod", ROOT / "run_local.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_local_mod"] = module
    spec.loader.exec_module(module)
    return module


_RL = _load_run_local()


def _sse(events: list[str]) -> bytes:
    return ("\n".join(events) + "\n").encode("utf-8")


def _openai_chunk(choice_delta: dict[str, Any]) -> str:
    return "data: " + json.dumps({"choices": [{"index": 0, "delta": choice_delta}]})


def test_select_provider_prefers_openai_when_both_keys_present() -> None:
    cfg = _RL.select_provider({"OPENAI_API_KEY": "sk-a", "ANTHROPIC_API_KEY": "ak-b"})
    assert cfg.name == "openai"
    assert cfg.api_key == "sk-a"


def test_select_provider_falls_back_to_anthropic_when_only_anthropic_set() -> None:
    cfg = _RL.select_provider({"ANTHROPIC_API_KEY": "ak-b"})
    assert cfg.name == "anthropic"
    assert cfg.api_key == "ak-b"


def test_select_provider_raises_when_no_keys() -> None:
    with pytest.raises(RuntimeError):
        _RL.select_provider({})


def test_select_provider_force_anthropic_overrides_openai() -> None:
    cfg = _RL.select_provider(
        {
            "LOOP_SUPPORT_PROVIDER": "anthropic",
            "OPENAI_API_KEY": "sk-a",
            "ANTHROPIC_API_KEY": "ak-b",
        }
    )
    assert cfg.name == "anthropic"


def test_run_turn_openai_streams_text_and_invokes_lookup_order() -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        seen.append(body)
        msgs = body["messages"]
        if len(msgs) == 2:
            # First hop: emit a tool call for lookup_order.
            chunks = [
                _openai_chunk(
                    {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_abc",
                                "type": "function",
                                "function": {
                                    "name": "lookup_order",
                                    "arguments": '{"order_id":',
                                },
                            }
                        ]
                    }
                ),
                _openai_chunk(
                    {
                        "tool_calls": [
                            {
                                "index": 0,
                                "function": {"arguments": '"4172"}'},
                            }
                        ]
                    }
                ),
                "data: [DONE]",
            ]
            return httpx.Response(200, content=_sse(chunks))
        # Second hop: model has tool result, emit the final answer.
        assert msgs[-1]["role"] == "tool"
        chunks = [
            _openai_chunk({"content": "Order 4172 is "}),
            _openai_chunk({"content": "in transit."}),
            "data: [DONE]",
        ]
        return httpx.Response(200, content=_sse(chunks))

    transport = httpx.MockTransport(handler)
    cfg = _RL.ProviderConfig(
        name="openai",
        base_url="https://api.openai.test",
        api_key="sk-test",
        model="gpt-4o-mini",
    )
    deltas: list[str] = []
    text = asyncio.run(
        _RL.run_turn(
            "where is order 4172?",
            cfg=cfg,
            transport=transport,
            on_delta=deltas.append,
        )
    )
    assert text == "Order 4172 is in transit."
    assert "".join(deltas) == "Order 4172 is in transit."
    assert len(seen) == 2
    # Tool result was sent back with the matching call id and the lookup payload.
    tool_msg = seen[1]["messages"][-1]
    assert tool_msg["role"] == "tool"
    assert tool_msg["tool_call_id"] == "call_abc"
    payload = json.loads(tool_msg["content"])
    assert payload["order_id"] == "4172"
    assert payload["status"] == "in_transit"


def test_run_turn_anthropic_streams_text_and_invokes_lookup_order() -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        seen.append(body)
        if len(body["messages"]) == 1:
            chunks = [
                "event: content_block_start",
                "data: "
                + json.dumps(
                    {
                        "index": 0,
                        "content_block": {
                            "type": "tool_use",
                            "id": "toolu_1",
                            "name": "lookup_order",
                        },
                    }
                ),
                "",
                "event: content_block_delta",
                "data: "
                + json.dumps(
                    {"index": 0, "delta": {"partial_json": '{"order_id":"4172"}'}}
                ),
                "",
                "event: message_stop",
                "data: {}",
                "",
            ]
            return httpx.Response(200, content=_sse(chunks))
        chunks = [
            "event: content_block_delta",
            "data: " + json.dumps({"index": 0, "delta": {"text": "Order 4172 is in transit."}}),
            "",
            "event: message_stop",
            "data: {}",
            "",
        ]
        return httpx.Response(200, content=_sse(chunks))

    transport = httpx.MockTransport(handler)
    cfg = _RL.ProviderConfig(
        name="anthropic",
        base_url="https://api.anthropic.test",
        api_key="ak-test",
        model="claude-3-5-haiku-latest",
    )
    deltas: list[str] = []
    text = asyncio.run(
        _RL.run_turn(
            "where is order 4172?",
            cfg=cfg,
            transport=transport,
            on_delta=deltas.append,
        )
    )
    assert text == "Order 4172 is in transit."
    assert "".join(deltas) == "Order 4172 is in transit."
    assert len(seen) == 2
    last_user = seen[1]["messages"][-1]
    assert last_user["role"] == "user"
    tool_result = last_user["content"][0]
    assert tool_result["type"] == "tool_result"
    assert tool_result["tool_use_id"] == "toolu_1"
    payload = json.loads(tool_result["content"])
    assert payload["status"] == "in_transit"


def test_run_turn_openai_propagates_4xx_as_runtime_error() -> None:
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(401, content=b'{"error":"bad key"}')

    cfg = _RL.ProviderConfig(
        name="openai",
        base_url="https://api.openai.test",
        api_key="sk-bad",
        model="gpt-4o-mini",
    )
    with pytest.raises(RuntimeError, match="401"):
        asyncio.run(
            _RL.run_turn(
                "ping",
                cfg=cfg,
                transport=httpx.MockTransport(handler),
            )
        )
