"""Integration test for cp ↔ dp turn bridge (S160).

Covers the path the studio's "Test turn" button exercises:

1. Studio POSTs to ``POST /v1/agents/{id}/test-turn`` with the user's
   session bearer.
2. cp resolves the agent's workspace, mints an audit event, and
   forwards the bearer + canonical ``RuntimeTurnRequest`` shape to
   dp's ``/v1/turns``.
3. dp's response is returned to the studio verbatim.

We mock dp via an httpx ``MockTransport`` so the test runs against the
real cp app (FastAPI TestClient) without a separate dp process.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient

from loop_control_plane import _routes_agent_turns as turns_module
from loop_control_plane.app import create_app
from loop_control_plane.paseto import encode_local

_TEST_KEY = b"x" * 32


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOOP_CP_PASETO_LOCAL_KEY", _TEST_KEY.decode())
    monkeypatch.setenv("LOOP_OTEL_ENDPOINT", "disabled")


@pytest.fixture
def client(env: None) -> TestClient:
    return TestClient(create_app())


def _bearer_for(sub: str) -> str:
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    token = encode_local(
        claims={"sub": sub},
        key=_TEST_KEY,
        now_ms=now_ms,
        expires_in_ms=3600 * 1000,
    )
    return f"Bearer {token}"


def _auth(sub: str = "owner-1") -> dict[str, str]:
    return {"authorization": _bearer_for(sub)}


def _workspace(client: TestClient) -> UUID:
    response = client.post(
        "/v1/workspaces",
        headers=_auth(),
        json={"name": "Acme", "slug": "acme"},
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def _agent(client: TestClient, workspace_id: UUID) -> UUID:
    response = client.post(
        "/v1/agents",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"name": "Support Bot", "slug": "support-bot"},
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def _create_version(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> int:
    response = client.post(
        f"/v1/agents/{agent_id}/versions",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "spec": {
                "name": "support-bot",
                "model": "gpt-4o-mini",
                "system_prompt": "You are Acme's support concierge.",
            },
            "notes": "first version",
        },
    )
    assert response.status_code == 201, response.text
    return int(response.json()["version"])


def test_version_get_by_number_and_active(client: TestClient) -> None:
    """cp exposes the new GET routes dp-runtime calls to resolve spec."""
    workspace_id = _workspace(client)
    agent_id = _agent(client, workspace_id)
    version = _create_version(client, workspace_id, agent_id)

    by_number = client.get(
        f"/v1/agents/{agent_id}/versions/{version}",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert by_number.status_code == 200, by_number.text
    body = by_number.json()
    assert body["version"] == version
    assert body["spec"]["model"] == "gpt-4o-mini"

    # 'active' returns 404 until the version is promoted — that's the
    # signal dp uses to fall back / surface a clean draft state.
    active_before = client.get(
        f"/v1/agents/{agent_id}/versions/active",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert active_before.status_code == 404, active_before.text

    version_id = body["id"]
    promote = client.post(
        f"/v1/agents/{agent_id}/versions/{version_id}/promote",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert promote.status_code == 200, promote.text

    active_after = client.get(
        f"/v1/agents/{agent_id}/versions/active",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert active_after.status_code == 200, active_after.text
    assert active_after.json()["version"] == version


def test_test_turn_proxies_to_dp(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """cp /test-turn forwards the user's bearer + payload to dp and
    returns dp's JSON response verbatim."""
    workspace_id = _workspace(client)
    agent_id = _agent(client, workspace_id)
    _create_version(client, workspace_id, agent_id)

    received: dict[str, object] = {}

    def _dp_handler(request: httpx.Request) -> httpx.Response:
        received["url"] = str(request.url)
        received["authorization"] = request.headers.get("authorization")
        received["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "turn_id": "trn_test_001",
                "reply": {"text": "Hello from the agent."},
                "events": [],
            },
        )

    transport = httpx.MockTransport(_dp_handler)

    # Patch the AsyncClient ctor used inside the proxy so it talks to
    # our in-process transport instead of opening a socket.
    original_client = turns_module.httpx.AsyncClient

    def _patched_client(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs.pop("transport", None)
        return original_client(*args, transport=transport, **kwargs)

    monkeypatch.setattr(turns_module.httpx, "AsyncClient", _patched_client)

    response = client.post(
        f"/v1/agents/{agent_id}/test-turn",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"input": "Hi, how do I reset my password?"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["turn_id"] == "trn_test_001"
    assert payload["reply"]["text"] == "Hello from the agent."

    # dp got the right shape.
    body = received["body"]
    assert isinstance(body, dict)
    assert body["agent_id"] == str(agent_id)
    assert body["workspace_id"] == str(workspace_id)
    assert body["input"] == "Hi, how do I reset my password?"
    assert body["user_id"] == "owner-1"
    assert "conversation_id" in body
    # cp forwards the user's bearer verbatim (dp verifies it).
    auth = received["authorization"]
    assert isinstance(auth, str) and auth.startswith("Bearer ")


def test_test_turn_unknown_agent_returns_404(client: TestClient) -> None:
    bogus = UUID("00000000-0000-0000-0000-000000000001")
    response = client.post(
        f"/v1/agents/{bogus}/test-turn",
        headers=_auth(),
        json={"input": "anyone home?"},
    )
    assert response.status_code == 404, response.text


def test_test_turn_dp_5xx_surfaces_as_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If dp errors out, cp surfaces a 502 with the dp body trimmed."""
    workspace_id = _workspace(client)
    agent_id = _agent(client, workspace_id)
    _create_version(client, workspace_id, agent_id)

    def _dp_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="gateway exploded")

    transport = httpx.MockTransport(_dp_handler)
    original_client = turns_module.httpx.AsyncClient

    def _patched_client(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs.pop("transport", None)
        return original_client(*args, transport=transport, **kwargs)

    monkeypatch.setattr(turns_module.httpx, "AsyncClient", _patched_client)

    response = client.post(
        f"/v1/agents/{agent_id}/test-turn",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"input": "ping"},
    )
    assert response.status_code == 502, response.text
    assert "gateway exploded" in response.text
