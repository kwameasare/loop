from __future__ import annotations

from datetime import UTC, datetime, timedelta
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


def test_expired_preapproved_class_is_revoked_before_preflight_and_audited(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
) -> None:
    _complete_commitment(client, workspace_id, agent_id)
    created = client.post(
        f"/v1/agents/{agent_id}/pre-approved-classes",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "granted_to_user_id": "owner-1",
            "allowed_change_types": ["instruction"],
            "excluded_change_types": ["tool", "memory", "channel", "budget"],
            "risk_ceiling": "low",
            "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "reason": "Short-lived instruction corridor.",
        },
    )
    assert created.status_code == 201, created.text
    class_id = created.json()["id"]
    registry = client.app.state.cp.preapproved_classes  # type: ignore[attr-defined]
    record = registry._items[agent_id][0]
    registry._items[agent_id][0] = record.model_copy(
        update={"expires_at": datetime.now(UTC) - timedelta(seconds=1)}
    )

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
    assert package["pre_approved_classes"] == []
    assert package["approval_status"] == "blocked"

    listed = client.get(
        f"/v1/agents/{agent_id}/pre-approved-classes",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert listed.status_code == 200, listed.text
    item = listed.json()["items"][0]
    assert item["id"] == class_id
    assert item["status"] == "expired"
    assert item["expired_at"] is not None
    assert item["revoked_at"] is not None

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    expiry_event = next(
        event for event in audit if event["action"] == "pre_approved_class:expire"
    )
    assert expiry_event["resource_id"] == class_id
    payload = fetch_payload(
        client.app.state.cp.audit_events,  # type: ignore[attr-defined]
        expiry_event["payload_hash"],
    )
    assert payload is not None
    assert payload["trigger"] == "change_package_preflight"


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


def test_preapproved_class_is_invalidated_when_policy_changes_affect_scope(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
) -> None:
    created = client.post(
        f"/v1/agents/{agent_id}/pre-approved-classes",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "granted_to_user_id": "owner-1",
            "allowed_change_types": ["instruction"],
            "excluded_change_types": ["memory", "tool", "channel"],
            "risk_ceiling": "low",
            "expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
            "reason": "Instruction-only edits while memory policy remains stable.",
        },
    )
    assert created.status_code == 201, created.text
    class_id = created.json()["id"]

    changed_policy = client.put(
        f"/v1/agents/{agent_id}/memory-policies/user",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "scope": "user",
            "allowed_memory_types": ["preference"],
            "retention": "Keep confirmed preferences for 90 days.",
            "consent_requirement": "Explicit consent required.",
            "pii_policy": "Do not store payment data.",
            "delete_behavior": "Delete on request with audit trail.",
            "privacy_implications": [
                "Durable preference affects future conversations for this user.",
            ],
            "source_trace_required": True,
        },
    )
    assert changed_policy.status_code == 200, changed_policy.text

    listed = client.get(
        f"/v1/agents/{agent_id}/pre-approved-classes",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert listed.status_code == 200, listed.text
    item = listed.json()["items"][0]
    assert item["id"] == class_id
    assert item["status"] == "invalidated"
    assert item["invalidated_at"] is not None
    assert "Memory policy" in item["reason"]

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    policy_event = next(
        event for event in audit if event["action"] == "memory_policy:upsert"
    )
    payload = fetch_payload(
        client.app.state.cp.audit_events,  # type: ignore[attr-defined]
        policy_event["payload_hash"],
    )
    assert payload is not None
    assert class_id in payload["invalidated_pre_approved_classes"]
