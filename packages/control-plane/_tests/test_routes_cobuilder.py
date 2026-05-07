"""Tests for the AI Co-Builder workspace route."""

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
        claims={"sub": sub},
        key=_TEST_KEY,
        now_ms=now_ms,
        expires_in_ms=3600 * 1000,
    )
    return f"Bearer {token}"


@pytest.fixture
def client(env: None) -> TestClient:
    return TestClient(create_app())


def _workspace(client: TestClient) -> UUID:
    return UUID(
        client.post(
            "/v1/workspaces",
            headers={"authorization": _bearer_for("owner-1")},
            json={"name": "Acme", "slug": "acme"},
        ).json()["id"]
    )


def _agent(client: TestClient, workspace_id: UUID) -> UUID:
    response = client.post(
        "/v1/agents",
        headers={
            "authorization": _bearer_for("owner-1"),
            "x-loop-workspace-id": str(workspace_id),
        },
        json={"name": "Support Bot", "slug": "support-bot"},
    )
    return UUID(response.json()["id"])


def test_cobuilder_derives_actions_from_latest_agent_version(
    client: TestClient,
) -> None:
    workspace_id = _workspace(client)
    agent_id = _agent(client, workspace_id)
    headers = {"authorization": _bearer_for("owner-1")}
    client.post(
        f"/v1/agents/{agent_id}/versions",
        headers=headers,
        json={
            "spec": {
                "system_prompt": "Answer refunds with evidence.",
                "tools": ["lookup_order", "issue_refund"],
                "memory_rules": ["preferred_language"],
            }
        },
    )

    response = client.get(
        f"/v1/workspaces/{workspace_id}/cobuilder",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["agentId"] == str(agent_id)
    assert body["operator"]["maxMode"] == "drive"
    assert "tools:write" in body["operator"]["scopes"]
    assert any(
        action["id"] == "act_gate_side_effect_tool" for action in body["actions"]
    )
    assert body["rubberDuck"]["proposedFix"]["id"] == body["review"]["actionId"]
    assert len(body["review"]["bullets"]) == 5


def test_cobuilder_downgrades_viewer_consent(
    client: TestClient,
) -> None:
    workspace_id = _workspace(client)
    client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers={"authorization": _bearer_for("owner-1")},
        json={"user_sub": "viewer-1", "role": "viewer"},
    )

    response = client.get(
        f"/v1/workspaces/{workspace_id}/cobuilder",
        headers={"authorization": _bearer_for("viewer-1")},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["operator"]["maxMode"] == "suggest"
    assert body["operator"]["scopes"] == ["agent:read"]
    assert body["actions"][0]["id"] == "act_create_first_agent"
