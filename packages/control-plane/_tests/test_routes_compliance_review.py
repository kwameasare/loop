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
        json={"name": "Refund Agent", "slug": "refund-agent"},
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def _seed_compliance_inputs(
    client: TestClient,
    *,
    workspace_id: UUID,
    agent_id: UUID,
) -> None:
    headers = {**_auth(), "x-loop-workspace-id": str(workspace_id)}
    tool = client.put(
        f"/v1/agents/{agent_id}/tool-contracts/refund_payment",
        headers=headers,
        json={
            "name": "Refund payment",
            "description": "Moves money back to customers.",
            "side_effect_level": "money_movement",
            "pii_access": True,
            "money_movement": True,
            "rate_limits": {"per_minute": 30},
            "budget_limits": {},
            "sandbox_status": "sandbox",
            "owner_user_id": "finance@acme",
            "failure_behavior": "Escalate failed refunds to finance.",
            "compensation_behavior": "",
        },
    )
    assert tool.status_code == 200, tool.text

    memory = client.put(
        f"/v1/agents/{agent_id}/memory-policies/user",
        headers=headers,
        json={
            "scope": "user",
            "allowed_memory_types": ["customer_preference"],
            "retention": "Retain for 90 days.",
            "consent_requirement": "Ask before storing support preferences.",
            "pii_policy": "May include personal support preferences.",
            "delete_behavior": "Delete on user request with audit trail.",
            "privacy_implications": ["May store user-level preferences."],
            "source_trace_required": True,
        },
    )
    assert memory.status_code == 200, memory.text

    channel = client.post(
        f"/v1/agents/{agent_id}/channel-bindings",
        headers=headers,
        json={
            "channel_type": "whatsapp",
            "provider": "Meta Cloud API",
            "display_name": "WhatsApp support",
            "status": "draft",
            "identity_config": {"business_id": "biz_123"},
        },
    )
    assert channel.status_code == 201, channel.text
    binding_id = channel.json()["id"]
    readiness = client.post(
        f"/v1/agents/{agent_id}/channel-bindings/{binding_id}/readiness/business_verified",
        headers=headers,
        json={
            "status": "failed",
            "evidence_ref": "channel/whatsapp/business",
            "message": "Business identity is not verified.",
        },
    )
    assert readiness.status_code == 200, readiness.text

    package = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers=headers,
        json={
            "summary": "Allow production refund automation.",
            "target_environment": "production",
            "risk_summary": "PII and payment path changed.",
            "tool_changes": [{"tool_id": "refund_payment", "change": "grant live use"}],
            "memory_changes": [{"scope": "user", "change": "durable support memory"}],
            "eval_results_ref": "evals/refund-safety/run-1",
            "replay_results_ref": "replay/refund-safety/run-1",
        },
    )
    assert package.status_code == 201, package.text

    incident = client.post(
        f"/v1/agents/{agent_id}/incidents/anomaly",
        headers=headers,
        json={
            "severity": "high",
            "trigger": "Refund quote regressed in WhatsApp canary.",
            "affected_trace_ids": ["trace_refund_1"],
            "affected_conversation_count": 4,
            "channel_scope": ["whatsapp"],
            "created_from": "test",
        },
    )
    assert incident.status_code == 201, incident.text


def test_compliance_review_aggregates_reviewer_surfaces(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
) -> None:
    _seed_compliance_inputs(client, workspace_id=workspace_id, agent_id=agent_id)

    response = client.get(
        f"/v1/workspaces/{workspace_id}/compliance-review",
        headers=_auth(),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["summary"]["agents"] == 1
    assert body["summary"]["pending_approvals"] >= 1
    assert body["summary"]["tool_reviews"] == 1
    assert body["summary"]["memory_reviews"] == 1
    assert body["summary"]["channel_blockers"] >= 1
    assert body["summary"]["open_incidents"] == 1
    assert "Compliance reviewer" in {row["role"] for row in body["approval_queue"]}
    assert body["tool_grants"][0]["reviewer_action"].startswith("Block live use")
    assert body["memory_policies"][0]["reviewer_action"].startswith("Review")
    assert body["channel_readiness"][0]["blocking_checks"]
    assert body["incidents"][0]["trigger"] == "Refund quote regressed in WhatsApp canary."
    assert body["industry_probe_libraries"][0]["id"] == "regulated-support"


def test_compliance_evidence_export_is_audited(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
) -> None:
    _seed_compliance_inputs(client, workspace_id=workspace_id, agent_id=agent_id)

    response = client.post(
        f"/v1/workspaces/{workspace_id}/compliance-review/evidence-export",
        headers=_auth(),
        json={
            "agent_id": str(agent_id),
            "format": "json",
            "include_sections": ["change_packages", "approvals", "audit_events"],
        },
    )

    assert response.status_code == 201, response.text
    export = response.json()
    assert export["status"] == "ready"
    assert export["sections"] == ["change_packages", "approvals", "audit_events"]
    assert any(ref.startswith("change-package/") for ref in export["artifact_refs"])
    assert export["download_url"].endswith(export["id"])

    audit = client.get(f"/v1/audit-events?workspace_id={workspace_id}", headers=_auth())
    assert audit.status_code == 200, audit.text
    assert "compliance:evidence_export" in {item["action"] for item in audit.json()["items"]}
