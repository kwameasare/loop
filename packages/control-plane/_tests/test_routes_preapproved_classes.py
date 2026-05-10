from __future__ import annotations

from datetime import UTC, datetime, timedelta
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


def _auth(sub: str = "owner-1") -> dict[str, str]:
    return {"authorization": _bearer_for(sub)}


@pytest.fixture
def client(env: None) -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def workspace_id(client: TestClient) -> UUID:
    response = client.post(
        "/v1/workspaces",
        headers=_auth(),
        json={"name": "Acme", "slug": "acme"},
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


@pytest.fixture
def agent_id(client: TestClient, workspace_id: UUID) -> UUID:
    response = client.post(
        "/v1/agents",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"name": "Support Bot", "slug": "support-bot"},
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def _complete_commitment(client: TestClient, workspace_id: UUID, agent_id: UUID) -> None:
    body = {
        "business_responsibility": "Resolve billing cancellations safely.",
        "target_users": "Enterprise customers.",
        "owner_user_id": "owner-1",
        "backup_owner_user_id": "backup-1",
        "worst_case_failure": "Refund outside policy.",
        "channels": ["web"],
        "systems_touched": ["billing"],
        "regions": ["us-east-1"],
        "languages": ["en"],
        "success_metric": "",
        "compliance_domain": "",
        "expected_volume": "",
        "launch_date": "",
        "budget_target": "",
        "out_of_scope": "",
        "escalation_policy": "Escalate policy conflicts.",
    }
    drafted = client.post(
        f"/v1/agents/{agent_id}/commitment",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"body": body, "created_from": "test"},
    )
    assert drafted.status_code == 201, drafted.text
    accepted = client.post(
        f"/v1/agents/{agent_id}/commitment/accept",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert accepted.status_code == 200, accepted.text


def test_preapproved_class_can_cover_instruction_only_preflight(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
) -> None:
    _complete_commitment(client, workspace_id, agent_id)
    expires = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    created = client.post(
        f"/v1/agents/{agent_id}/pre-approved-classes",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "granted_to_user_id": "owner-1",
            "allowed_change_types": ["instruction"],
            "excluded_change_types": ["tool", "memory", "channel", "budget"],
            "risk_ceiling": "low",
            "expires_at": expires,
            "reason": "Instruction-only copy fixes for the launch window.",
        },
    )
    assert created.status_code == 201, created.text
    class_id = created.json()["id"]

    generated = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "target_environment": "production",
            "semantic_diff": [
                {
                    "dimension": "instruction",
                    "summary": "Clarifies refund deadline copy.",
                    "evidence_ref": "behavior/sentence/refund_deadline",
                }
            ],
            "summary": "Instruction-only refund copy clarification.",
        },
    )
    assert generated.status_code == 201, generated.text
    package = generated.json()
    assert package["pre_approved_classes"][0]["id"] == class_id
    assert package["approval_status"] == "approved"
    assert {item["state"] for item in package["required_approvals"]} >= {"pre_approved"}

    listed = client.get(
        f"/v1/agents/{agent_id}/pre-approved-classes",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert listed.status_code == 200, listed.text
    assert package["id"] in listed.json()["items"][0]["used_by_change_packages"]


def test_preapproved_class_does_not_cover_excluded_or_high_risk_change(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
) -> None:
    _complete_commitment(client, workspace_id, agent_id)
    client.post(
        f"/v1/agents/{agent_id}/pre-approved-classes",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "granted_to_user_id": "owner-1",
            "allowed_change_types": ["instruction"],
            "excluded_change_types": ["tool"],
            "risk_ceiling": "low",
            "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "reason": "Instruction-only edits.",
        },
    )

    generated = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "target_environment": "production",
            "tool_changes": [{"tool_id": "refund_api", "change": "grant write"}],
            "summary": "Adds a mutating refund tool.",
        },
    )
    assert generated.status_code == 201, generated.text
    package = generated.json()
    assert package["pre_approved_classes"] == []
    assert package["approval_status"] == "blocked"
    assert any(
        approval["state"] == "requested" and approval["role"] == "Compliance reviewer"
        for approval in package["required_approvals"]
    )


def test_preapproved_class_creation_requires_narrow_explicit_boundaries(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
) -> None:
    missing_exclusions = client.post(
        f"/v1/agents/{agent_id}/pre-approved-classes",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "granted_to_user_id": "owner-1",
            "allowed_change_types": ["instruction"],
            "excluded_change_types": [],
            "risk_ceiling": "low",
            "expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
            "reason": "Instruction-only edits.",
        },
    )
    assert missing_exclusions.status_code == 400, missing_exclusions.text
    assert "excluded change types" in missing_exclusions.text

    high_risk = client.post(
        f"/v1/agents/{agent_id}/pre-approved-classes",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "granted_to_user_id": "owner-1",
            "allowed_change_types": ["instruction"],
            "excluded_change_types": ["tool", "memory", "channel", "budget"],
            "risk_ceiling": "high",
            "expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
            "reason": "Overbroad approval bypass.",
        },
    )
    assert high_risk.status_code == 400, high_risk.text
    assert "high-risk" in high_risk.text

    long_lived = client.post(
        f"/v1/agents/{agent_id}/pre-approved-classes",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "granted_to_user_id": "owner-1",
            "allowed_change_types": ["instruction"],
            "excluded_change_types": ["tool", "memory", "channel", "budget"],
            "risk_ceiling": "low",
            "expires_at": (datetime.now(UTC) + timedelta(days=31)).isoformat(),
            "reason": "Too long to be a narrow approval corridor.",
        },
    )
    assert long_lived.status_code == 400, long_lived.text
    assert "30 days" in long_lived.text
