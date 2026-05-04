"""Run the support_agent against a real LLM provider.

This script is the runnable wiring for the example: it takes a question,
streams the model's response from OpenAI or Anthropic, executes the
``lookup_order`` tool when the model asks for it, and prints the final
answer.

Provider selection (in order):

* ``OPENAI_API_KEY`` set → OpenAI ``gpt-4o-mini`` via
  ``https://api.openai.com/v1/chat/completions``.
* ``ANTHROPIC_API_KEY`` set → Anthropic ``claude-3-5-haiku-latest`` via
  ``https://api.anthropic.com/v1/messages``.

Both endpoints are reached over ``httpx``. Tests substitute a
``httpx.MockTransport`` to replay deterministic cassettes — see
``examples/support_agent/_tests/test_run_local.py``.

Usage::

    OPENAI_API_KEY=sk-... \
        uv run python examples/support_agent/run_local.py "where is order 4172?"

Environment overrides:

* ``LOOP_SUPPORT_PROVIDER`` — force ``openai`` or ``anthropic``.
* ``LOOP_SUPPORT_OPENAI_BASE_URL`` / ``LOOP_SUPPORT_ANTHROPIC_BASE_URL`` —
  base URL overrides for proxies and integration fixtures.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any

import httpx

# Allow running as a script without a packaged install.
sys.path.insert(0, os.path.dirname(__file__))

from agent import LOOKUP_ORDER_TOOL_SCHEMA, lookup_order  # type: ignore[import-not-found]

OPENAI_BASE_URL_DEFAULT = "https://api.openai.com"
ANTHROPIC_BASE_URL_DEFAULT = "https://api.anthropic.com"
ANTHROPIC_VERSION = "2023-06-01"

ToolDispatcher = Callable[[str, Mapping[str, Any]], Awaitable[Mapping[str, Any]]]


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key: str
    model: str


def select_provider(env: Mapping[str, str] | None = None) -> ProviderConfig:
    env = env if env is not None else os.environ
    forced = (env.get("LOOP_SUPPORT_PROVIDER") or "").strip().lower()
    openai_key = env.get("OPENAI_API_KEY")
    anthropic_key = env.get("ANTHROPIC_API_KEY")

    if forced == "openai" or (forced == "" and openai_key):
        if not openai_key:
            raise RuntimeError("OPENAI_API_KEY is required for the OpenAI provider")
        return ProviderConfig(
            name="openai",
            base_url=env.get("LOOP_SUPPORT_OPENAI_BASE_URL", OPENAI_BASE_URL_DEFAULT),
            api_key=openai_key,
            model=env.get("LOOP_SUPPORT_OPENAI_MODEL", "gpt-4o-mini"),
        )
    if forced == "anthropic" or anthropic_key:
        if not anthropic_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for the Anthropic provider")
        return ProviderConfig(
            name="anthropic",
            base_url=env.get("LOOP_SUPPORT_ANTHROPIC_BASE_URL", ANTHROPIC_BASE_URL_DEFAULT),
            api_key=anthropic_key,
            model=env.get("LOOP_SUPPORT_ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
        )
    raise RuntimeError(
        "Set OPENAI_API_KEY or ANTHROPIC_API_KEY to run the support_agent example."
    )


SYSTEM_PROMPT = (
    "You are a friendly customer support agent for an online retailer.\n"
    "- Use lookup_order when the user asks about an order.\n"
    '- If you don\'t know, say "I don\'t know" and offer to escalate.\n'
    "- Never invent order details."
)


async def _default_lookup_order(name: str, args: Mapping[str, Any]) -> Mapping[str, Any]:
    if name != "lookup_order":
        raise ValueError(f"unknown tool: {name}")
    return await lookup_order(str(args.get("order_id", "")))


async def _stream_lines(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: Mapping[str, str],
    json_body: Mapping[str, Any],
) -> AsyncIterator[str]:
    async with client.stream(method, url, headers=dict(headers), json=dict(json_body)) as resp:
        if resp.status_code >= 400:
            text = (await resp.aread()).decode("utf-8", errors="replace")
            raise RuntimeError(f"{resp.status_code} from upstream: {text[:200]}")
        async for line in resp.aiter_lines():
            yield line


async def _openai_turn(
    cfg: ProviderConfig,
    question: str,
    *,
    client: httpx.AsyncClient,
    on_delta: Callable[[str], None],
    dispatch: ToolDispatcher,
) -> str:
    """Execute one tool-using turn against the OpenAI Chat Completions API.

    Returns the model's final assistant text.
    """

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": LOOKUP_ORDER_TOOL_SCHEMA["name"],
                "description": LOOKUP_ORDER_TOOL_SCHEMA["description"],
                "parameters": LOOKUP_ORDER_TOOL_SCHEMA["input_schema"],
            },
        }
    ]
    final_text = ""
    for _hop in range(2):  # at most: tool-call hop, then text hop
        body = {
            "model": cfg.model,
            "stream": True,
            "messages": messages,
            "tools": tools,
        }
        headers = {
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        text_buf: list[str] = []
        tool_calls: dict[int, dict[str, Any]] = {}
        async for raw in _stream_lines(
            client, "POST", f"{cfg.base_url}/v1/chat/completions",
            headers=headers, json_body=body,
        ):
            line = raw.strip()
            if not line.startswith("data:"):
                continue
            payload = line[len("data:") :].strip()
            if payload == "[DONE]":
                break
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            choice = (obj.get("choices") or [{}])[0]
            delta = choice.get("delta") or {}
            if content := delta.get("content"):
                text_buf.append(content)
                on_delta(content)
            for tc in delta.get("tool_calls") or []:
                idx = int(tc.get("index", 0))
                slot = tool_calls.setdefault(
                    idx, {"id": "", "name": "", "arguments": ""}
                )
                if cid := tc.get("id"):
                    slot["id"] = cid
                fn = tc.get("function") or {}
                if fname := fn.get("name"):
                    slot["name"] = fname
                if fargs := fn.get("arguments"):
                    slot["arguments"] = slot["arguments"] + fargs
        if not tool_calls:
            final_text = "".join(text_buf)
            break
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": "".join(text_buf) or None,
            "tool_calls": [
                {
                    "id": slot["id"] or f"call_{i}",
                    "type": "function",
                    "function": {"name": slot["name"], "arguments": slot["arguments"] or "{}"},
                }
                for i, slot in tool_calls.items()
            ],
        }
        messages.append(assistant_msg)
        for slot in tool_calls.values():
            try:
                args = json.loads(slot["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}
            result = await dispatch(slot["name"], args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": slot["id"],
                    "content": json.dumps(dict(result)),
                }
            )
    return final_text


async def _anthropic_turn(
    cfg: ProviderConfig,
    question: str,
    *,
    client: httpx.AsyncClient,
    on_delta: Callable[[str], None],
    dispatch: ToolDispatcher,
) -> str:
    """Execute one tool-using turn against Anthropic Messages API."""

    messages: list[dict[str, Any]] = [{"role": "user", "content": question}]
    tools = [
        {
            "name": LOOKUP_ORDER_TOOL_SCHEMA["name"],
            "description": LOOKUP_ORDER_TOOL_SCHEMA["description"],
            "input_schema": LOOKUP_ORDER_TOOL_SCHEMA["input_schema"],
        }
    ]
    final_text = ""
    for _hop in range(2):
        body = {
            "model": cfg.model,
            "max_tokens": 512,
            "system": SYSTEM_PROMPT,
            "stream": True,
            "messages": messages,
            "tools": tools,
        }
        headers = {
            "x-api-key": cfg.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        text_buf: list[str] = []
        blocks: dict[int, dict[str, Any]] = {}
        cur_event: str | None = None
        async for raw in _stream_lines(
            client, "POST", f"{cfg.base_url}/v1/messages",
            headers=headers, json_body=body,
        ):
            line = raw.strip()
            if not line:
                cur_event = None
                continue
            if line.startswith("event:"):
                cur_event = line[len("event:") :].strip()
                continue
            if not line.startswith("data:"):
                continue
            payload = line[len("data:") :].strip()
            try:
                obj = json.loads(payload) if payload else {}
            except json.JSONDecodeError:
                continue
            if cur_event == "content_block_start":
                idx = int(obj.get("index", 0))
                cb = obj.get("content_block") or {}
                blocks[idx] = {
                    "type": cb.get("type", ""),
                    "name": cb.get("name", ""),
                    "id": cb.get("id", ""),
                    "input": "",
                }
            elif cur_event == "content_block_delta":
                idx = int(obj.get("index", 0))
                d = obj.get("delta") or {}
                if text := d.get("text"):
                    text_buf.append(text)
                    on_delta(text)
                if partial := d.get("partial_json"):
                    blocks.setdefault(idx, {"type": "tool_use", "input": ""})
                    blocks[idx]["input"] = blocks[idx].get("input", "") + partial
            elif cur_event == "message_stop":
                break
        tool_blocks = [b for b in blocks.values() if b.get("type") == "tool_use"]
        if not tool_blocks:
            final_text = "".join(text_buf)
            break
        assistant_content: list[dict[str, Any]] = []
        if text := "".join(text_buf):
            assistant_content.append({"type": "text", "text": text})
        for b in tool_blocks:
            try:
                args = json.loads(b.get("input") or "{}")
            except json.JSONDecodeError:
                args = {}
            assistant_content.append(
                {"type": "tool_use", "id": b["id"], "name": b["name"], "input": args}
            )
        messages.append({"role": "assistant", "content": assistant_content})
        tool_results: list[dict[str, Any]] = []
        for b in tool_blocks:
            try:
                args = json.loads(b.get("input") or "{}")
            except json.JSONDecodeError:
                args = {}
            result = await dispatch(b["name"], args)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": b["id"],
                    "content": json.dumps(dict(result)),
                }
            )
        messages.append({"role": "user", "content": tool_results})
    return final_text


async def run_turn(
    question: str,
    *,
    cfg: ProviderConfig | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
    on_delta: Callable[[str], None] | None = None,
    dispatch: ToolDispatcher | None = None,
) -> str:
    """Run one tool-using turn against the configured provider.

    Returns the final assistant text. Tests pass a ``transport`` (e.g.
    ``httpx.MockTransport``) and a synthetic ``cfg`` to exercise the
    full streaming + tool-call flow without touching the network.
    """

    cfg = cfg or select_provider()
    on_delta = on_delta or (lambda _t: None)
    dispatch = dispatch or _default_lookup_order
    async with httpx.AsyncClient(transport=transport, timeout=30.0) as client:
        if cfg.name == "openai":
            return await _openai_turn(
                cfg, question, client=client, on_delta=on_delta, dispatch=dispatch
            )
        if cfg.name == "anthropic":
            return await _anthropic_turn(
                cfg, question, client=client, on_delta=on_delta, dispatch=dispatch
            )
        raise RuntimeError(f"unknown provider {cfg.name}")


def main(argv: list[str] | None = None) -> int:
    import asyncio

    args = list(argv if argv is not None else sys.argv[1:])
    question = "where is order 4172?" if not args else " ".join(args)
    cfg = select_provider()
    sys.stdout.write(f"[{cfg.name}:{cfg.model}] {question}\n")
    sys.stdout.flush()

    def _print(chunk: str) -> None:
        sys.stdout.write(chunk)
        sys.stdout.flush()

    final = asyncio.run(run_turn(question, cfg=cfg, on_delta=_print))
    if final and not final.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
