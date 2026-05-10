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


def _commitment_body() -> dict[str, object]:
    return {
        "business_responsibility": "Resolve support questions with policy evidence.",
        "target_users": "Enterprise customers.",
        "owner_user_id": "owner-1",
        "backup_owner_user_id": "backup-1",
        "worst_case_failure": "Promises refunds outside policy.",
        "channels": ["web", "whatsapp"],
        "systems_touched": ["crm"],
        "regions": ["us-east-1"],
        "languages": ["en"],
        "success_metric": "95% eval pass rate.",
        "compliance_domain": "SOC2 support",
        "expected_volume": "10k turns/month",
        "launch_date": "2026-06-01",
        "budget_target": "$0.08/turn",
        "out_of_scope": "Legal advice.",
        "escalation_policy": "Escalate legal threats and refund exceptions.",
    }


def test_agent_commitment_routes_resolve_workspace_from_agent_id(
    client: TestClient,
) -> None:
    _workspace_id = _workspace(client)
    agent_id = _agent(client, _workspace_id)

    saved = client.post(
        f"/v1/agents/{agent_id}/commitment",
        headers=_auth(),
        json={"body": _commitment_body(), "created_from": "test:agent_scoped"},
    )
    assert saved.status_code == 201, saved.text
    assert saved.json()["workspace_id"] == str(_workspace_id)

    current = client.get(f"/v1/agents/{agent_id}/commitment/current", headers=_auth())
    assert current.status_code == 200, current.text
    assert current.json()["id"] == saved.json()["id"]

    accepted = client.post(f"/v1/agents/{agent_id}/commitment/accept", headers=_auth())
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"


def test_change_package_routes_resolve_workspace_from_agent_id(
    client: TestClient,
) -> None:
    workspace_id = _workspace(client)
    agent_id = _agent(client, workspace_id)
    saved = client.post(
        f"/v1/agents/{agent_id}/commitment",
        headers=_auth(),
        json={"body": _commitment_body(), "created_from": "test:agent_scoped"},
    )
    assert saved.status_code == 201, saved.text
    assert client.post(f"/v1/agents/{agent_id}/commitment/accept", headers=_auth()).status_code == 200

    generated = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers=_auth(),
        json={
            "summary": "Preflight without workspace header.",
            "eval_results_ref": "eval/run-agent-scoped",
            "replay_results_ref": "replay/run-agent-scoped",
            "channel_readiness_summary": "web_chat draft binding is ready for sandbox.",
        },
    )
    assert generated.status_code == 201, generated.text
    package = generated.json()
    assert package["workspace_id"] == str(workspace_id)

    current = client.get(f"/v1/agents/{agent_id}/change-packages/current", headers=_auth())
    assert current.status_code == 200, current.text
    assert current.json()["item"]["id"] == package["id"]

    submitted = client.post(
        f"/v1/agents/{agent_id}/change-packages/{package['id']}/submit",
        headers=_auth(),
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "submitted"

    approved = client.post(
        f"/v1/agents/{agent_id}/change-packages/{package['id']}/approvals",
        headers=_auth(),
        json={"approval_id": "owner", "decision": "approve", "comment": "Reviewed."},
    )
    assert approved.status_code == 200, approved.text
    assert any(
        approval["id"] == "owner" and approval["state"] == "approved"
        for approval in approved.json()["required_approvals"]
    )
