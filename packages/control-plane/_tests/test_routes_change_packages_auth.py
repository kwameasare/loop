"""Authorization tests for Change Package review-control paths."""

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

    added = client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers=owner,
        json={"user_sub": "alice", "role": "member"},
    )
    assert added.status_code == 201, added.text
    return workspace_id, UUID(agent.json()["id"])


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


def _accept_commitment(client: TestClient, agent_id: UUID) -> None:
    drafted = client.post(
        f"/v1/agents/{agent_id}/commitment",
        headers=_auth(),
        json={"body": _commitment_body(), "created_from": "test:change_package_auth"},
    )
    assert drafted.status_code == 201, drafted.text
    accepted = client.post(f"/v1/agents/{agent_id}/commitment/accept", headers=_auth())
    assert accepted.status_code == 200, accepted.text


def _generate_package(client: TestClient, agent_id: UUID) -> dict[str, object]:
    generated = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers=_auth(),
        json={
            "from_version_id": "v1",
            "to_version_id": "v2",
            "summary": "Change Package authorization fixture.",
            "eval_results_ref": "eval/run-change-package-auth",
            "replay_results_ref": "replay/run-change-package-auth",
            "rollback_target_version_id": "v1",
        },
    )
    assert generated.status_code == 201, generated.text
    return generated.json()


def test_members_can_read_but_not_generate_change_packages(
    client: TestClient,
    workspace_and_agent: tuple[UUID, UUID],
) -> None:
    _, agent_id = workspace_and_agent
    _accept_commitment(client, agent_id)
    member = _auth("alice")

    listed = client.get(f"/v1/agents/{agent_id}/change-packages", headers=member)
    assert listed.status_code == 200, listed.text

    current = client.get(f"/v1/agents/{agent_id}/change-packages/current", headers=member)
    assert current.status_code == 200, current.text

    denied = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers=member,
        json={
            "from_version_id": "v1",
            "to_version_id": "v2",
            "summary": "Member should not generate production review evidence.",
            "eval_results_ref": "eval/member-denied",
            "replay_results_ref": "replay/member-denied",
            "rollback_target_version_id": "v1",
        },
    )
    assert denied.status_code == 403


def test_members_cannot_submit_or_approve_change_packages(
    client: TestClient,
    workspace_and_agent: tuple[UUID, UUID],
) -> None:
    _, agent_id = workspace_and_agent
    _accept_commitment(client, agent_id)
    package = _generate_package(client, agent_id)
    member = _auth("alice")

    denied_submit = client.post(
        f"/v1/agents/{agent_id}/change-packages/{package['id']}/submit",
        headers=member,
    )
    assert denied_submit.status_code == 403

    submitted = client.post(
        f"/v1/agents/{agent_id}/change-packages/{package['id']}/submit",
        headers=_auth(),
    )
    assert submitted.status_code == 200, submitted.text

    denied_approval = client.post(
        f"/v1/agents/{agent_id}/change-packages/{package['id']}/approvals",
        headers=member,
        json={"approval_id": "owner", "decision": "approve"},
    )
    assert denied_approval.status_code == 403

