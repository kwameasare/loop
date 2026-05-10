"""Authorization tests for agent channel binding write paths."""

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
    added = client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers=owner,
        json={"user_sub": "alice", "role": "member"},
    )
    assert added.status_code == 201, added.text
    return workspace_id, UUID(agent.json()["id"])


def test_members_can_read_but_not_configure_channel_bindings(
    client: TestClient,
    workspace_and_agent: tuple[UUID, UUID],
) -> None:
    _, agent_id = workspace_and_agent
    member = {"authorization": _bearer_for("alice")}

    read = client.get(f"/v1/agents/{agent_id}/channel-bindings", headers=member)
    assert read.status_code == 200, read.text

    write = client.post(
        f"/v1/agents/{agent_id}/channel-bindings",
        headers=member,
        json={
            "channel_type": "whatsapp",
            "provider": "Meta Cloud API",
            "display_name": "WhatsApp",
            "status": "draft",
            "identity_config": {"handle": "+15550101010"},
            "auth_config_ref": "vault://channels/whatsapp",
        },
    )
    assert write.status_code == 403


def test_members_cannot_mutate_channel_readiness(
    client: TestClient,
    workspace_and_agent: tuple[UUID, UUID],
) -> None:
    _, agent_id = workspace_and_agent
    owner = {"authorization": _bearer_for("owner-1")}
    member = {"authorization": _bearer_for("alice")}

    created = client.post(
        f"/v1/agents/{agent_id}/channel-bindings",
        headers=owner,
        json={
            "channel_type": "whatsapp",
            "provider": "Meta Cloud API",
            "display_name": "WhatsApp",
            "status": "draft",
            "identity_config": {"handle": "+15550101010"},
            "auth_config_ref": "vault://channels/whatsapp",
        },
    )
    assert created.status_code == 201, created.text
    binding_id = created.json()["id"]

    denied = client.post(
        f"/v1/agents/{agent_id}/channel-bindings/{binding_id}/readiness/business_verified",
        headers=member,
        json={
            "status": "passed",
            "evidence_ref": "channels/whatsapp/business_verified",
            "message": "Verified by Meta.",
        },
    )
    assert denied.status_code == 403


def test_members_cannot_record_channel_activity(
    client: TestClient,
    workspace_and_agent: tuple[UUID, UUID],
) -> None:
    _, agent_id = workspace_and_agent
    owner = {"authorization": _bearer_for("owner-1")}
    member = {"authorization": _bearer_for("alice")}

    created = client.post(
        f"/v1/agents/{agent_id}/channel-bindings",
        headers=owner,
        json={
            "channel_type": "whatsapp",
            "provider": "Meta Cloud API",
            "display_name": "WhatsApp",
            "status": "draft",
            "identity_config": {"handle": "+15550101010"},
            "auth_config_ref": "vault://channels/whatsapp",
        },
    )
    assert created.status_code == 201, created.text
    binding_id = created.json()["id"]

    denied = client.post(
        f"/v1/agents/{agent_id}/channel-bindings/{binding_id}/activity",
        headers=member,
        json={"status": "success", "trace_id": "trace_123"},
    )
    assert denied.status_code == 403
