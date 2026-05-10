"""Tests for agent web-channel provisioning routes."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from loop_control_plane.app import create_app
from loop_control_plane.audit_events import fetch_payload
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
def workspace_and_agent(client: TestClient) -> tuple[UUID, UUID]:
    owner = {"authorization": _bearer_for("owner-1")}
    workspace = client.post(
        "/v1/workspaces",
        headers=owner,
        json={"name": "Acme", "slug": "acme"},
    )
    assert workspace.status_code == 201, workspace.text
    workspace_id = UUID(workspace.json()["id"])
    agent = client.post(
        "/v1/agents",
        headers={**owner, "X-Loop-Workspace-Id": str(workspace_id)},
        json={"name": "Support Concierge", "slug": "support-concierge"},
    )
    assert agent.status_code == 201, agent.text
    return workspace_id, UUID(agent.json()["id"])


def test_get_web_channel_starts_disabled(
    client: TestClient,
    workspace_and_agent: tuple[UUID, UUID],
) -> None:
    _, agent_id = workspace_and_agent
    response = client.get(
        f"/v1/agents/{agent_id}/channels/web",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "agentId": str(agent_id),
        "status": "disabled",
        "channelId": None,
        "token": None,
        "enabledAt": None,
    }


def test_enable_web_channel_mints_token_and_updates_channel_readiness(
    client: TestClient,
    workspace_and_agent: tuple[UUID, UUID],
) -> None:
    workspace_id, agent_id = workspace_and_agent
    headers = {"authorization": _bearer_for("owner-1")}
    enabled = client.post(
        f"/v1/agents/{agent_id}/channels/web/enable",
        headers=headers,
    )
    assert enabled.status_code == 200, enabled.text
    body = enabled.json()
    assert body["agentId"] == str(agent_id)
    assert body["status"] == "enabled"
    assert body["channelId"].startswith("wch_")
    assert body["token"].startswith("wct_")
    assert body["enabledAt"]

    listed = client.get(f"/v1/agents/{agent_id}/channel-bindings", headers=headers)
    web_binding = next(
        item for item in listed.json()["items"] if item["channel_type"] == "web_chat"
    )
    assert web_binding["status"] == "draft"
    assert web_binding["auth_config_ref"] == f"web-channel/{body['channelId']}"
    snippet_check = next(
        check for check in web_binding["readiness"] if check["id"] == "snippet_minted"
    )
    assert snippet_check["status"] == "passed"
    assert snippet_check["evidence_ref"] == f"web-channel/{body['channelId']}/snippet"

    state = client.app.state.cp  # type: ignore[attr-defined]
    rows = list(state.audit_events.list_for_workspace(workspace_id))
    enable_row = next(row for row in rows if row.action == "web_channel:enable")
    assert enable_row.payload_hash
    payload = fetch_payload(state.audit_events, enable_row.payload_hash)
    assert payload is not None
    assert body["token"] not in repr(payload)
    assert payload["channel_id"] == body["channelId"]


def test_disable_web_channel_revokes_public_token_and_pauses_binding(
    client: TestClient,
    workspace_and_agent: tuple[UUID, UUID],
) -> None:
    _, agent_id = workspace_and_agent
    headers = {"authorization": _bearer_for("owner-1")}
    enabled = client.post(
        f"/v1/agents/{agent_id}/channels/web/enable",
        headers=headers,
    ).json()

    disabled = client.post(
        f"/v1/agents/{agent_id}/channels/web/disable",
        headers=headers,
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json() == {
        "agentId": str(agent_id),
        "status": "disabled",
        "channelId": None,
        "token": None,
        "enabledAt": None,
    }

    current = client.get(f"/v1/agents/{agent_id}/channels/web", headers=headers)
    assert current.json()["token"] is None
    assert enabled["token"] not in repr(current.json())

    listed = client.get(f"/v1/agents/{agent_id}/channel-bindings", headers=headers)
    web_binding = next(
        item for item in listed.json()["items"] if item["channel_type"] == "web_chat"
    )
    assert web_binding["status"] == "paused"
    assert web_binding["auth_config_ref"] is None


def test_web_channel_mutation_requires_admin_but_member_can_read(
    client: TestClient,
    workspace_and_agent: tuple[UUID, UUID],
) -> None:
    workspace_id, agent_id = workspace_and_agent
    owner = {"authorization": _bearer_for("owner-1")}
    member = {"authorization": _bearer_for("alice")}
    added = client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers=owner,
        json={"user_sub": "alice", "role": "member"},
    )
    assert added.status_code == 201, added.text

    read = client.get(f"/v1/agents/{agent_id}/channels/web", headers=member)
    assert read.status_code == 200, read.text

    denied = client.post(
        f"/v1/agents/{agent_id}/channels/web/enable",
        headers=member,
    )
    assert denied.status_code == 403
