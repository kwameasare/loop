"""FastAPI route for Studio Multi-Agent Conductor wire-up."""

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
    response = client.post(
        "/v1/workspaces",
        headers={"authorization": _bearer_for("owner-1")},
        json={"name": "Acme", "slug": "acme"},
    )
    return UUID(response.json()["id"])


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


def test_agent_conductor_route_reads_version_topology(
    client: TestClient, agent_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    client.post(
        f"/v1/agents/{agent_id}/versions",
        headers=headers,
        json={
            "spec": {
                "sub_agents": [
                    {
                        "id": "sub_refund",
                        "name": "Refund Specialist",
                        "purpose": "Handle refund policy.",
                        "owner": "Revenue",
                    }
                ],
                "handoff_contracts": [
                    {
                        "id": "contract_refund",
                        "name": "Refund handoff",
                        "from": "sub_intake",
                        "to": "sub_refund",
                        "state": "ready",
                    }
                ],
            }
        },
    )

    response = client.get(f"/v1/agents/{agent_id}/conductor", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["agentName"] == "Support Bot"
    assert body["subAgents"][0]["name"] == "Refund Specialist"
    assert body["contracts"][0]["name"] == "Refund handoff"
    assert body["topology"][0]["target"] == "sub_refund"


def test_agent_conductor_route_requires_workspace_membership(
    client: TestClient, agent_id: UUID
) -> None:
    response = client.get(
        f"/v1/agents/{agent_id}/conductor",
        headers={"authorization": _bearer_for("stranger")},
    )
    assert response.status_code in (401, 403)
