"""Authorization tests for agent lifecycle and Commitment Document mutations."""

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


def _commitment_body() -> dict[str, object]:
    return {
        "business_responsibility": "Resolve billing cancellation requests safely.",
        "target_users": "Existing enterprise customers and support operators.",
        "owner_user_id": "owner-1",
        "backup_owner_user_id": "backup-1",
        "worst_case_failure": "Incorrectly promises a refund outside policy.",
        "channels": ["web", "whatsapp"],
        "systems_touched": ["billing", "crm"],
        "regions": ["us-east-1"],
        "languages": ["en"],
        "success_metric": "95% eval pass rate before canary.",
        "compliance_domain": "SOC2 support operations",
        "expected_volume": "20k turns per month",
        "launch_date": "2026-06-01",
        "budget_target": "$0.08 per resolved turn",
        "out_of_scope": "Legal advice and payment disputes above $500.",
        "escalation_policy": "Escalate policy conflicts to support lead.",
    }


@pytest.fixture
def workspace_and_agent(client: TestClient) -> tuple[UUID, UUID]:
    owner = _auth()
    workspace = client.post(
        "/v1/workspaces",
        headers=owner,
        json={"name": "Acme", "slug": "acme"},
    )
    assert workspace.status_code == 201, workspace.text
    workspace_id = UUID(workspace.json()["id"])

    agent = client.post(
        "/v1/agents",
        headers={**owner, "x-loop-workspace-id": str(workspace_id)},
        json={"name": "Support Concierge", "slug": "support-concierge"},
    )
    assert agent.status_code == 201, agent.text

    member = client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers=owner,
        json={"user_sub": "alice", "role": "member"},
    )
    assert member.status_code == 201, member.text
    return workspace_id, UUID(agent.json()["id"])


def test_members_can_read_but_not_create_or_archive_agents(
    client: TestClient,
    workspace_and_agent: tuple[UUID, UUID],
) -> None:
    workspace_id, agent_id = workspace_and_agent
    member = {**_auth("alice"), "x-loop-workspace-id": str(workspace_id)}

    listed = client.get("/v1/agents", headers=member)
    assert listed.status_code == 200, listed.text

    detail = client.get(f"/v1/agents/{agent_id}", headers=_auth("alice"))
    assert detail.status_code == 200, detail.text

    denied_create = client.post(
        "/v1/agents",
        headers=member,
        json={"name": "Unauthorized Agent", "slug": "unauthorized-agent"},
    )
    assert denied_create.status_code == 403

    denied_archive = client.delete(f"/v1/agents/{agent_id}", headers=_auth("alice"))
    assert denied_archive.status_code == 403


def test_members_can_read_but_not_mutate_commitment_documents(
    client: TestClient,
    workspace_and_agent: tuple[UUID, UUID],
) -> None:
    _, agent_id = workspace_and_agent
    member = _auth("alice")

    current = client.get(f"/v1/agents/{agent_id}/commitment/current", headers=member)
    assert current.status_code == 200, current.text

    history = client.get(f"/v1/agents/{agent_id}/commitments", headers=member)
    assert history.status_code == 200, history.text

    denied_draft = client.post(
        f"/v1/agents/{agent_id}/commitment",
        headers=member,
        json={"body": _commitment_body(), "created_from": "test:member_denied"},
    )
    assert denied_draft.status_code == 403

    owner_draft = client.post(
        f"/v1/agents/{agent_id}/commitment",
        headers=_auth(),
        json={"body": _commitment_body(), "created_from": "test:owner_allowed"},
    )
    assert owner_draft.status_code == 201, owner_draft.text

    denied_accept = client.post(
        f"/v1/agents/{agent_id}/commitment/accept",
        headers=member,
    )
    assert denied_accept.status_code == 403

