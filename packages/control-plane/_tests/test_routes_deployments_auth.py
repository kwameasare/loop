"""Authorization tests for deployment and evidence-pack write paths."""

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

    member = client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers=owner,
        json={"user_sub": "alice", "role": "member"},
    )
    assert member.status_code == 201, member.text
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


def _mark_channel_ready(client: TestClient, agent_id: UUID, channel_type: str) -> None:
    created = client.post(
        f"/v1/agents/{agent_id}/channel-bindings",
        headers=_auth(),
        json={
            "channel_type": channel_type,
            "provider": "Loop Test",
            "display_name": f"Test {channel_type}",
            "status": "ready",
            "identity_config": {"test": True},
            "auth_config_ref": "secret://test/channel",
        },
    )
    assert created.status_code == 201, created.text
    binding = created.json()
    for check in binding["readiness"]:
        checked = client.post(
            f"/v1/agents/{agent_id}/channel-bindings/{binding['id']}/readiness/{check['id']}",
            headers=_auth(),
            json={
                "status": "passed",
                "evidence_ref": f"test/{channel_type}/{check['id']}",
                "message": "Verified in deployment authorization test.",
            },
        )
        assert checked.status_code == 200, checked.text


def _approved_change_package(client: TestClient, agent_id: UUID) -> dict[str, object]:
    drafted = client.post(
        f"/v1/agents/{agent_id}/commitment",
        headers=_auth(),
        json={"body": _commitment_body(), "created_from": "test:deployment_auth"},
    )
    assert drafted.status_code == 201, drafted.text
    accepted = client.post(f"/v1/agents/{agent_id}/commitment/accept", headers=_auth())
    assert accepted.status_code == 200, accepted.text

    generated = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers=_auth(),
        json={
            "from_version_id": "v1",
            "to_version_id": "v2",
            "summary": "Deployment authorization package.",
            "eval_results_ref": "eval/run-deployment-auth",
            "replay_results_ref": "replay/run-deployment-auth",
            "rollback_target_version_id": "v1",
        },
    )
    assert generated.status_code == 201, generated.text
    package = generated.json()

    submitted = client.post(
        f"/v1/agents/{agent_id}/change-packages/{package['id']}/submit",
        headers=_auth(),
    )
    assert submitted.status_code == 200, submitted.text

    for approval_id in ("owner", "compliance"):
        approved = client.post(
            f"/v1/agents/{agent_id}/change-packages/{package['id']}/approvals",
            headers=_auth(),
            json={"approval_id": approval_id, "decision": "approve"},
        )
        assert approved.status_code == 200, approved.text
        package = approved.json()
    assert package["status"] == "approved"
    return package


def _start_deployment(client: TestClient, agent_id: UUID) -> dict[str, object]:
    _mark_channel_ready(client, agent_id, "web_chat")
    package = _approved_change_package(client, agent_id)
    started = client.post(
        f"/v1/agents/{agent_id}/deployments/start",
        headers=_auth(),
        json={
            "change_package_id": package["id"],
            "version_id": "v2",
            "traffic_percent": 10,
            "channel_scope": ["web_chat"],
            "auto_rollback_thresholds": {"error_rate": 0.02},
        },
    )
    assert started.status_code == 201, started.text
    return started.json()["deployment"]


def test_members_can_read_but_not_start_deployments(
    client: TestClient,
    workspace_and_agent: tuple[UUID, UUID],
) -> None:
    _, agent_id = workspace_and_agent
    member = _auth("alice")

    listed = client.get(f"/v1/agents/{agent_id}/deployments", headers=member)
    assert listed.status_code == 200, listed.text

    denied = client.post(
        f"/v1/agents/{agent_id}/deployments/start",
        headers=member,
        json={
            "change_package_id": "cp_unreachable",
            "version_id": "v2",
            "traffic_percent": 10,
            "channel_scope": ["web_chat"],
        },
    )
    assert denied.status_code == 403


def test_members_cannot_mutate_existing_deployments(
    client: TestClient,
    workspace_and_agent: tuple[UUID, UUID],
) -> None:
    _, agent_id = workspace_and_agent
    deployment = _start_deployment(client, agent_id)
    member = _auth("alice")
    deployment_id = deployment["id"]

    mutating_requests = [
        ("post", f"/v1/agents/{agent_id}/deployments/{deployment_id}/promote", None),
        (
            "post",
            f"/v1/agents/{agent_id}/deployments/{deployment_id}/ramp",
            {"traffic_percent": 50},
        ),
        ("post", f"/v1/agents/{agent_id}/deployments/{deployment_id}/pause", None),
        (
            "post",
            f"/v1/agents/{agent_id}/deployments/{deployment_id}/rollback",
            {"mode": "manual", "reason": "operator requested rollback"},
        ),
        (
            "post",
            f"/v1/agents/{agent_id}/deployments/{deployment_id}/thresholds/evaluate",
            {
                "metric": "error_rate",
                "observed": 0.03,
                "policy": "rollback",
                "window": "5m",
            },
        ),
    ]
    for method, path, json_body in mutating_requests:
        response = getattr(client, method)(path, headers=member, json=json_body)
        assert response.status_code == 403, response.text


def test_members_can_list_but_not_export_evidence_packs(
    client: TestClient,
    workspace_and_agent: tuple[UUID, UUID],
) -> None:
    _, agent_id = workspace_and_agent
    _start_deployment(client, agent_id)
    member = _auth("alice")

    listed = client.get(f"/v1/agents/{agent_id}/evidence-packs", headers=member)
    assert listed.status_code == 200, listed.text
    pack = listed.json()["items"][0]

    denied = client.post(
        f"/v1/agents/{agent_id}/evidence-packs/{pack['id']}/exports",
        headers=member,
        json={"format": "json", "purpose": "member export attempt"},
    )
    assert denied.status_code == 403

