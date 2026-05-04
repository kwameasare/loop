"""Streaming turn error envelope redaction tests."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from loop_data_plane._turns import RuntimeTurnRequest, stream_turn_sse
from loop_runtime import AgentConfig, TurnBudget

WORKSPACE_ID = UUID("11111111-1111-4111-8111-111111111111")
CONVERSATION_ID = UUID("22222222-2222-4222-8222-222222222222")


class _ProviderFailure(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class _FailingExecutor:
    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    async def execute(
        self,
        _agent: AgentConfig,
        _event: object,
        *,
        request_id: str,
    ) -> AsyncIterator[object]:
        raise self._exc
        yield  # pragma: no cover


def _request() -> RuntimeTurnRequest:
    return RuntimeTurnRequest(
        workspace_id=WORKSPACE_ID,
        conversation_id=CONVERSATION_ID,
        user_id="user-redaction",
        input="hello",
        request_id="turn-redacted",
        budget=TurnBudget(),
    )


async def _stream_error_payload(exc: BaseException) -> dict[str, str]:
    body = b"".join([chunk async for chunk in stream_turn_sse(_FailingExecutor(exc), _request())])
    block = body.decode().strip()
    data = next(line.removeprefix("data: ") for line in block.splitlines() if line.startswith("data: "))
    return json.loads(data)


@pytest.mark.asyncio
async def test_streaming_provider_5xx_error_is_redacted() -> None:
    payload = await _stream_error_payload(
        _ProviderFailure(
            "LOOP-GW-401",
            "upstream 503 body leaked prompt='customer-ssn-1234' account=acct-secret",
        )
    )

    assert payload == {
        "code": "LOOP-GW-401",
        "message": "Provider request failed.",
        "request_id": "turn-redacted",
    }


@pytest.mark.asyncio
async def test_streaming_provider_401_maps_without_message_leak() -> None:
    payload = await _stream_error_payload(
        _ProviderFailure("LOOP-GW-101", "provider rejected sk-live-secret for workspace")
    )

    assert payload == {
        "code": "LOOP-GW-101",
        "message": "Provider credentials were rejected.",
        "request_id": "turn-redacted",
    }
