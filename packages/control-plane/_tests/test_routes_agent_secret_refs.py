"""Tests for agent-scoped secret reference routes.

Studio's agent Secrets tab must show vault/KMS references without ever
materialising credential values in the control plane response or audit payload.
"""

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
        json={"name": "Billing Support", "slug": "billing-support"},
    )
    assert agent.status_code == 201, agent.text
    return workspace_id, UUID(agent.json()["id"])


def test_create_and_list_agent_secret_ref_metadata_only(
    client: TestClient,
    workspace_and_agent: tuple[UUID, UUID],
) -> None:
    _, agent_id = workspace_and_agent
    headers = {"authorization": _bearer_for("owner-1")}

    created = client.post(
        f"/v1/agents/{agent_id}/secrets",
        headers=headers,
        json={"name": "OPENAI_API_KEY", "ref": "kms://prod/openai-key"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["agent_id"] == str(agent_id)
    assert body["name"] == "OPENAI_API_KEY"
    assert body["ref"] == "kms://prod/openai-key"
    assert body["rotated_at"] is None
    assert "value" not in body
    assert "workspace_id" not in body

    listed = client.get(f"/v1/agents/{agent_id}/secrets", headers=headers)
    assert listed.status_code == 200, listed.text
    assert listed.json()["items"] == [body]


def test_agent_secret_ref_rejects_plaintext_and_extra_fields(
    client: TestClient,
    workspace_and_agent: tuple[UUID, UUID],
) -> None:
    _, agent_id = workspace_and_agent
    headers = {"authorization": _bearer_for("owner-1")}

    plaintext = client.post(
        f"/v1/agents/{agent_id}/secrets",
        headers=headers,
        json={"name": "OPENAI_API_KEY", "ref": "sk-live-should-not-store"},
    )
    assert plaintext.status_code == 422

    value_field = client.post(
        f"/v1/agents/{agent_id}/secrets",
        headers=headers,
        json={
            "name": "OPENAI_API_KEY",
            "ref": "kms://prod/openai-key",
            "value": "sk-live-should-not-store",
        },
    )
    assert value_field.status_code == 422


def test_agent_secret_ref_writes_require_admin_but_member_can_list(
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

    created = client.post(
        f"/v1/agents/{agent_id}/secrets",
        headers=owner,
        json={"name": "STRIPE_SECRET", "ref": "vault://payments/stripe"},
    )
    assert created.status_code == 201, created.text

    listed = client.get(f"/v1/agents/{agent_id}/secrets", headers=member)
    assert listed.status_code == 200, listed.text
    assert listed.json()["items"][0]["name"] == "STRIPE_SECRET"

    denied = client.post(
        f"/v1/agents/{agent_id}/secrets",
        headers=member,
        json={"name": "TWILIO_TOKEN", "ref": "vault://voice/twilio"},
    )
    assert denied.status_code == 403


def test_rotate_agent_secret_ref_updates_evidence_and_audits_without_ref_path(
    client: TestClient,
    workspace_and_agent: tuple[UUID, UUID],
) -> None:
    workspace_id, agent_id = workspace_and_agent
    headers = {"authorization": _bearer_for("owner-1")}
    created = client.post(
        f"/v1/agents/{agent_id}/secrets",
        headers=headers,
        json={"name": "OPENAI_API_KEY", "ref": "kms://prod/openai-key"},
    ).json()

    rotated = client.post(
        f"/v1/secrets/{created['id']}/rotate",
        headers=headers,
        json={},
    )
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["secretId"] == created["id"]
    assert rotated.json()["rotated_at"]

    listed = client.get(f"/v1/agents/{agent_id}/secrets", headers=headers)
    listed_secret = listed.json()["items"][0]
    assert listed_secret["rotated_at"] == rotated.json()["rotated_at"]

    state = client.app.state.cp  # type: ignore[attr-defined]
    rows = list(state.audit_events.list_for_workspace(workspace_id))
    actions = [row.action for row in rows]
    assert "agent_secret_ref:create" in actions
    assert "agent_secret_ref:rotate" in actions
    payload_hashes = [row.payload_hash for row in rows if row.payload_hash]
    payloads = [fetch_payload(state.audit_events, payload_hash) for payload_hash in payload_hashes]
    payload_repr = repr(payloads)
    assert "kms://prod/openai-key" not in payload_repr
    assert "OPENAI_API_KEY" in payload_repr
    assert "'ref_kind': 'kms'" in payload_repr
