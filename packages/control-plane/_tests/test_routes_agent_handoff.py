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
        claims={"sub": sub},
        key=_TEST_KEY,
        now_ms=now_ms,
        expires_in_ms=3600 * 1000,
    )
    return f"Bearer {token}"


@pytest.fixture
def client(env: None) -> TestClient:
    return TestClient(create_app())


def _workspace(client: TestClient) -> UUID:
    return UUID(
        client.post(
            "/v1/workspaces",
            headers={"authorization": _bearer_for("owner-1")},
            json={"name": "Acme", "slug": "acme"},
        ).json()["id"]
    )


def _agent(client: TestClient, workspace_id: UUID) -> UUID:
    response = client.post(
        "/v1/agents",
        headers={
            "authorization": _bearer_for("owner-1"),
            "x-loop-workspace-id": str(workspace_id),
        },
        json={"name": "Support Bot", "slug": "support-bot"},
    )
    return UUID(response.json()["id"])


def test_handoff_walkthrough_and_owner_transfer_are_audited(
    client: TestClient,
) -> None:
    workspace_id = _workspace(client)
    agent_id = _agent(client, workspace_id)
    headers = {
        "authorization": _bearer_for("owner-1"),
        "x-loop-workspace-id": str(workspace_id),
    }
    comment = client.post(
        f"/v1/agents/{agent_id}/comments/cmt_handoff/resolve",
        headers=headers,
        json={
            "expected_behavior": "Escalate legal threats before quoting refunds.",
            "failure_reason": "Reviewer found a missed legal-threat escalation.",
            "also_create_eval_case": True,
            "source_trace": "trace_handoff_1",
        },
    )
    assert comment.status_code == 200, comment.text
    tool_contract = client.put(
        f"/v1/agents/{agent_id}/tool-contracts/refund_api",
        headers=headers,
        json={
            "name": "Refund API",
            "description": "Issues customer refunds.",
            "side_effect_level": "money_movement",
            "pii_access": True,
            "money_movement": True,
            "rate_limits": {"rpm": 30},
            "budget_limits": {},
            "sandbox_status": "sandbox",
            "owner_user_id": "",
            "approval_policy_id": "policy-money",
            "failure_behavior": "",
            "compensation_behavior": "",
        },
    )
    assert tool_contract.status_code == 200, tool_contract.text
    memory_policy = client.put(
        f"/v1/agents/{agent_id}/memory-policies/user",
        headers=headers,
        json={
            "scope": "user",
            "allowed_memory_types": ["language_preference"],
            "retention": "Retain until the user deletes the preference.",
            "consent_requirement": "User consent required before durable writes.",
            "pii_policy": "No secrets or government identifiers.",
            "delete_behavior": "Delete when the user requests deletion.",
            "privacy_implications": ["Stores durable user preference data."],
            "source_trace_required": True,
        },
    )
    assert memory_policy.status_code == 200, memory_policy.text
    suite = client.post(
        f"/v1/workspaces/{workspace_id}/eval-suites",
        headers=headers,
        json={
            "name": "Support Bot handoff coverage",
            "dataset_ref": f"agent:{agent_id}:handoff",
            "metrics": ["behavior_match"],
        },
    )
    assert suite.status_code == 201, suite.text
    case = client.post(
        f"/v1/eval-suites/{suite.json()['id']}/cases",
        headers=headers,
        json={
            "name": "Legal threat escalation",
            "input": {"message": "I will sue if you do not refund me."},
            "expected": {"behavior": "Escalate before quoting refund."},
            "scorers": [{"kind": "llm_judge", "config": {"rubric": "escalation"}}],
            "source": "handoff",
            "source_ref": f"agent:{agent_id}:handoff",
            "attachments": [str(agent_id)],
        },
    )
    assert case.status_code == 201, case.text

    initial = client.get(f"/v1/agents/{agent_id}/handoff", headers=headers)

    assert initial.status_code == 200, initial.text
    initial_body = initial.json()
    assert initial_body["agent"]["id"] == str(agent_id)
    assert any(risk["id"] == "commitment_missing_fields" for risk in initial_body["open_risks"])
    assert any(risk["id"] == "tool_contract_review_required" for risk in initial_body["open_risks"])
    assert any(risk["id"] == "memory_policy_review_required" for risk in initial_body["open_risks"])
    assert any(section["id"] == "commitments" for section in initial_body["walkthrough_sections"])
    tool_section = next(
        section
        for section in initial_body["walkthrough_sections"]
        if section["id"] == "tool-grants"
    )
    assert tool_section["count"] == 1
    assert tool_section["evidence_refs"] == [f"tool-contract/{tool_contract.json()['id']}"]
    memory_section = next(
        section
        for section in initial_body["walkthrough_sections"]
        if section["id"] == "memory-policies"
    )
    assert memory_section["count"] == 1
    assert memory_section["evidence_refs"] == [f"memory-policy/{memory_policy.json()['id']}"]
    eval_section = next(
        section
        for section in initial_body["walkthrough_sections"]
        if section["id"] == "eval-coverage"
    )
    assert eval_section["count"] == 1
    assert f"eval-suite/{suite.json()['id']}" in eval_section["evidence_refs"]
    assert f"eval/{case.json()['id']}" in eval_section["evidence_refs"]
    risk_section = next(
        section
        for section in initial_body["walkthrough_sections"]
        if section["id"] == "risk-posture"
    )
    assert risk_section["count"] >= 3
    assert any(ref.startswith("tool-contract/") for ref in risk_section["evidence_refs"])
    comments_section = next(
        section
        for section in initial_body["walkthrough_sections"]
        if section["id"] == "important-comments"
    )
    assert comments_section["count"] == 1
    assert comments_section["evidence_refs"] == [
        "comment/cmt_handoff -> eval/eval_comment_cmt_handoff"
    ]

    transferred = client.post(
        f"/v1/agents/{agent_id}/handoff/transfer",
        headers=headers,
        json={
            "new_owner_user_id": "new-owner@acme.test",
            "backup_owner_user_id": "backup@acme.test",
            "reason": "Platform team rotation",
            "acknowledged_risk_ids": ["commitment_missing_fields"],
        },
    )

    assert transferred.status_code == 200, transferred.text
    body = transferred.json()
    assert body["owner_user_id"] == "new-owner@acme.test"
    assert body["backup_owner_user_id"] == "backup@acme.test"
    assert body["transfers"][0]["previous_owner_user_id"] == ""
    assert body["transfers"][0]["new_owner_user_id"] == "new-owner@acme.test"
    assert body["transfers"][0]["history_walkthrough_id"].startswith("walk_")
    assert body["transfers"][0]["open_risk_ids"] == [
        "commitment_missing_fields",
        "tool_contract_review_required",
        "memory_policy_review_required",
    ]
    assert "important-comments" in body["transfers"][0]["walkthrough_section_ids"]
    assert body["transfers"][0]["notification"]["recipient"] == "new-owner@acme.test"
    assert body["commitment"]["created_from"] == "handoff:ownership_transfer"
    actions = [
        event.action
        for event in client.app.state.cp.audit_events.list_for_workspace(workspace_id)  # type: ignore[attr-defined]
    ]
    assert "agent_handoff:ownership_transfer" in actions
    transfer_event = next(
        event
        for event in client.app.state.cp.audit_events.list_for_workspace(workspace_id)  # type: ignore[attr-defined]
        if event.action == "agent_handoff:ownership_transfer"
    )
    payload = client.app.state.cp.audit_events.fetch_payload(  # type: ignore[attr-defined]
        transfer_event.payload_hash
    )
    assert payload["notification_recipient"] == "new-owner@acme.test"
    assert payload["open_risk_ids"] == [
        "commitment_missing_fields",
        "tool_contract_review_required",
        "memory_policy_review_required",
    ]
