"""FastAPI route for Studio Tools Room wire-up."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from loop_control_plane.app import create_app
from loop_control_plane.paseto import encode_local

_TEST_KEY = b"x" * 32


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOOP_CP_PASETO_LOCAL_KEY", _TEST_KEY.decode())
    monkeypatch.setenv("LOOP_OTEL_ENDPOINT", "disabled")


def _bearer_for(sub: str) -> str:
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    token = encode_local(
        claims={"sub": sub}, key=_TEST_KEY, now_ms=now_ms, expires_in_ms=3600 * 1000
    )
    return f"Bearer {token}"


@pytest.fixture
def client(env: None) -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def workspace_id(client: TestClient) -> UUID:
    return UUID(
        client.post(
            "/v1/workspaces",
            headers={"authorization": _bearer_for("owner-1")},
            json={"name": "Acme", "slug": "acme"},
        ).json()["id"]
    )


@pytest.fixture
def agent_id(client: TestClient, workspace_id: UUID) -> UUID:
    response = client.post(
        "/v1/agents",
        headers={
            "authorization": _bearer_for("owner-1"),
            "x-loop-workspace-id": str(workspace_id),
        },
        json={"name": "Support Bot", "slug": "support-bot"},
    )
    return UUID(response.json()["id"])


def test_agent_tools_route_reads_latest_version_spec(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    client.post(
        f"/v1/agents/{agent_id}/versions",
        headers=headers,
        json={
            "spec": {
                "tools": [
                    {
                        "id": "lookup_order",
                        "name": "lookup_order",
                        "kind": "http",
                        "description": "Look up order state.",
                        "source": "https://orders.example.test",
                    },
                    "kb.search",
                ]
            }
        },
    )

    response = client.get(f"/v1/agents/{agent_id}/tools", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["items"] == [
        {
            "id": "lookup_order",
            "name": "lookup_order",
            "kind": "http",
            "description": "Look up order state.",
            "source": "https://orders.example.test",
        },
        {
            "id": "kb.search",
            "name": "kb.search",
            "kind": "mcp",
            "description": "",
            "source": "agent-version-spec",
        },
    ]


def test_agent_tools_route_requires_workspace_membership(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    response = client.get(
        f"/v1/agents/{agent_id}/tools",
        headers={"authorization": _bearer_for("stranger")},
    )
    assert response.status_code in (401, 403)
