"""Real httpx streaming transports for first-party LLM providers."""

from __future__ import annotations

import json
import os
from asyncio import sleep
from collections.abc import AsyncIterator, Mapping
from typing import Any, Literal
from uuid import UUID

import httpx

from loop_gateway.byo_keys import (
    BYOKeyMissing,
    Vendor,
    WorkspaceKeyResolver,
    WorkspaceKeyStore,
)
from loop_gateway.types import GatewayMessage, GatewayRequest, ToolSpec

ProviderName = Literal["openai", "anthropic"]


class ProviderTransportError(RuntimeError):
    """Transport-level failure already mapped to a public gateway error code."""

    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class EmptyWorkspaceKeyStore:
    """Workspace key store used when only platform-default env keys are configured."""

    def get_for_model(self, workspace_id: UUID, model: str) -> str | None:
        return None

    def get_for_vendor(self, workspace_id: UUID, vendor: Vendor) -> str | None:
        return None


def resolver_from_env(
    key_store: WorkspaceKeyStore | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> WorkspaceKeyResolver:
    env = environ or os.environ
    defaults: dict[Vendor, str] = {}
    # Accept the LOOP_GATEWAY_*-prefixed names (production canonical) and
    # the bare OPENAI_API_KEY / ANTHROPIC_API_KEY (the names every other
    # tool in the ecosystem uses, including .env.example here). Prefixed
    # names win when both are set, so an operator can override the bare
    # default for a specific gateway tenant.
    openai_key = env.get("LOOP_GATEWAY_OPENAI_API_KEY") or env.get("OPENAI_API_KEY")
    if openai_key:
        defaults[Vendor.OPENAI] = openai_key
    anthropic_key = env.get("LOOP_GATEWAY_ANTHROPIC_API_KEY") or env.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        defaults[Vendor.ANTHROPIC] = anthropic_key
    return WorkspaceKeyResolver(key_store or EmptyWorkspaceKeyStore(), platform_defaults=defaults)


class HttpxStreamTransport:
    """POST provider streaming requests through ``httpx.AsyncClient.stream``."""

    def __init__(
        self,
        provider: ProviderName,
        *,
        key_resolver: WorkspaceKeyResolver | None = None,
        client: httpx.AsyncClient | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        retry_backoff_seconds: float = 0.05,
    ) -> None:
        self.provider = provider
        self._resolver = key_resolver or resolver_from_env()
        self._client = client
        self._base_url = (base_url or _default_base_url(provider)).rstrip("/")
        self._timeout = httpx.Timeout(
            timeout_seconds or float(os.environ.get("LOOP_GATEWAY_HTTP_TIMEOUT_SECONDS", "30"))
        )
        self._max_retries = (
            max_retries
            if max_retries is not None
            else int(os.environ.get("LOOP_GATEWAY_HTTP_MAX_RETRIES", "2"))
        )
        self._retry_backoff = retry_backoff_seconds

    async def __call__(self, request: GatewayRequest) -> AsyncIterator[str]:
        for attempt in range(self._max_retries + 1):
            try:
                async for line in self._stream_once(request):
                    yield line
                return
            except ProviderTransportError as exc:
                if not exc.retryable or attempt >= self._max_retries:
                    raise
                await sleep(self._retry_backoff * (attempt + 1))
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt >= self._max_retries:
                    raise ProviderTransportError("LOOP-GW-402", str(exc)) from exc
                await sleep(self._retry_backoff * (attempt + 1))

    async def _stream_once(self, request: GatewayRequest) -> AsyncIterator[str]:
        try:
            key = self._resolver.resolve(
                workspace_id=UUID(request.workspace_id),
                model=request.model,
            )
        except (BYOKeyMissing, ValueError) as exc:
            raise ProviderTransportError("LOOP-GW-101", str(exc)) from exc

        close_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            async with client.stream(
                "POST",
                self._url(),
                headers=self._headers(key.api_key),
                json=self._body(request),
            ) as response:
                if response.status_code >= 400:
                    await _raise_for_status(response)
                async for line in response.aiter_lines():
                    yield line
        finally:
            if close_client:
                await client.aclose()

    def _url(self) -> str:
        if self.provider == "openai":
            return f"{self._base_url}/v1/chat/completions"
        return f"{self._base_url}/v1/messages"

    def _headers(self, api_key: str) -> dict[str, str]:
        headers = {"accept": "text/event-stream", "content-type": "application/json"}
        if self.provider == "openai":
            return headers | {"authorization": f"Bearer {api_key}"}
        return headers | {"x-api-key": api_key, "anthropic-version": "2023-06-01"}

    def _body(self, request: GatewayRequest) -> dict[str, Any]:
        if self.provider == "openai":
            body: dict[str, Any] = {
                "model": request.model,
                "messages": [_openai_message(message) for message in request.messages],
                "stream": True,
                "stream_options": {"include_usage": True},
                "temperature": request.temperature,
            }
            if request.tools:
                body["tools"] = [_openai_tool(tool) for tool in request.tools]
            if request.max_output_tokens is not None:
                body["max_tokens"] = request.max_output_tokens
            return body
        system = "\n".join(m.content for m in request.messages if m.role == "system")
        body = {
            "model": request.model,
            "messages": [_anthropic_message(m) for m in request.messages if m.role != "system"],
            "stream": True,
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens or 1024,
        }
        if system:
            body["system"] = system
        if request.tools:
            body["tools"] = [_anthropic_tool(tool) for tool in request.tools]
        return body


async def _raise_for_status(response: httpx.Response) -> None:
    text = (await response.aread()).decode(errors="replace")[:500]
    if response.status_code == 429:
        raise ProviderTransportError("LOOP-GW-301", text or "provider rate limit", retryable=True)
    if response.status_code >= 500:
        raise ProviderTransportError("LOOP-GW-401", text or "provider 5xx", retryable=True)
    if response.status_code in {401, 403}:
        raise ProviderTransportError("LOOP-GW-101", text or "provider key rejected")
    raise ProviderTransportError("LOOP-GW-401", text or f"provider HTTP {response.status_code}")


def _default_base_url(provider: ProviderName) -> str:
    if provider == "openai":
        return "https://api.openai.com"
    return "https://api.anthropic.com"


def _openai_message(message: GatewayMessage) -> dict[str, Any]:
    payload: dict[str, Any] = {"role": message.role, "content": message.content}
    if message.tool_call_id:
        payload["tool_call_id"] = message.tool_call_id
    if message.name:
        payload["name"] = message.name
    if message.tool_calls:
        payload["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
            }
            for call in message.tool_calls
        ]
    return payload


def _openai_tool(tool: ToolSpec) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema,
        },
    }


def _anthropic_message(message: GatewayMessage) -> dict[str, Any]:
    role = "assistant" if message.role == "assistant" else "user"
    return {"role": role, "content": message.content}


def _anthropic_tool(tool: ToolSpec) -> dict[str, Any]:
    return {"name": tool.name, "description": tool.description, "input_schema": tool.input_schema}


__all__ = [
    "EmptyWorkspaceKeyStore",
    "HttpxStreamTransport",
    "ProviderTransportError",
    "resolver_from_env",
]
