"""Data-residency guard coverage for dp-runtime turns."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi.testclient import TestClient
from loop_data_plane.runtime_app import RuntimeAppState, create_app


class _ShouldNotRunExecutor:
    async def execute(
        self,
        *_args: object,
        **_kwargs: object,
    ) -> AsyncIterator[object]:
        raise AssertionError("cross-region guard should block before executor")
        yield  # pragma: no cover


def test_cross_region_callout_is_blocked_before_turn_execution(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LOOP_DP_AUTH_DISABLE", "1")
    monkeypatch.setenv("LOOP_OTEL_ENDPOINT", "disabled")
    app = create_app(RuntimeAppState(executor=_ShouldNotRunExecutor()))  # type: ignore[arg-type]
    client = TestClient(app)

    response = client.post(
        "/v1/turns",
        json={
            "workspace_id": "11111111-1111-4111-8111-111111111111",
            "conversation_id": "22222222-2222-4222-8222-222222222222",
            "user_id": "builder-1",
            "input": "call the tool",
            "metadata": {
                "workspace_region": "eu-west-2",
                "target_region": "us-east-1",
                "tool_name": "lookup_order",
            },
        },
    )

    assert response.status_code == 403, response.text
    assert response.json()["code"] == "LOOP-AC-602"
    assert "cross_region_blocked" in response.json()["message"]
