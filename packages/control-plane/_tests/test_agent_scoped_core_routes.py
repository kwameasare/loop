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


def _mark_channel_ready(client: TestClient, agent_id: UUID, channel_type: str) -> dict[str, object]:
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
                "message": "Verified in agent-scoped route test.",
            },
        )
        assert checked.status_code == 200, checked.text
        binding = checked.json()
    assert binding["status"] == "ready"
    assert {check["status"] for check in binding["readiness"]} == {"passed"}
    return binding


def _approved_change_package(client: TestClient, agent_id: UUID) -> dict[str, object]:
    drafted = client.post(
        f"/v1/agents/{agent_id}/commitment",
        headers=_auth(),
        json={"body": _commitment_body(), "created_from": "test:agent_scoped"},
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
            "summary": "Agent-scoped rollout package.",
            "eval_results_ref": "eval/run-agent-scoped",
            "replay_results_ref": "replay/run-agent-scoped",
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


def test_agent_detail_resolves_workspace_from_agent_id(
    client: TestClient,
) -> None:
    workspace_id = _workspace(client)
    agent_id = _agent(client, workspace_id)

    response = client.get(f"/v1/agents/{agent_id}", headers=_auth())
    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(agent_id)
    assert response.json()["object_state"] == "draft"


def test_channel_and_deployment_routes_resolve_workspace_from_agent_id(
    client: TestClient,
) -> None:
    workspace_id = _workspace(client)
    agent_id = _agent(client, workspace_id)
    package = _approved_change_package(client, agent_id)
    _mark_channel_ready(client, agent_id, "web_chat")

    started = client.post(
        f"/v1/agents/{agent_id}/deployments/start",
        headers=_auth(),
        json={
            "change_package_id": package["id"],
            "version_id": "v2",
            "traffic_percent": 10,
            "channel_scope": ["web_chat"],
        },
    )
    assert started.status_code == 201, started.text
    deployment = started.json()["deployment"]
    assert deployment["channelScope"] == ["web_chat"]

    listed = client.get(f"/v1/agents/{agent_id}/deployments", headers=_auth())
    assert listed.status_code == 200, listed.text
    assert listed.json()["items"][0]["id"] == deployment["id"]

    evidence = client.get(f"/v1/agents/{agent_id}/evidence-packs", headers=_auth())
    assert evidence.status_code == 200, evidence.text
    pack = evidence.json()["items"][0]
    exported = client.post(
        f"/v1/agents/{agent_id}/evidence-packs/{pack['id']}/exports",
        headers=_auth(),
        json={"format": "json", "purpose": "agent-scoped route test"},
    )
    assert exported.status_code == 201, exported.text
    assert exported.json()["workspace_id"] == str(workspace_id)


def test_operational_agent_routes_resolve_workspace_from_agent_id(
    client: TestClient,
) -> None:
    _workspace_id = _workspace(client)
    agent_id = _agent(client, _workspace_id)

    handoff = client.get(f"/v1/agents/{agent_id}/handoff", headers=_auth())
    assert handoff.status_code == 200, handoff.text
    assert handoff.json()["agent"]["id"] == str(agent_id)

    expires_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    preapproved = client.post(
        f"/v1/agents/{agent_id}/pre-approved-classes",
        headers=_auth(),
        json={
            "granted_to_user_id": "owner-1",
            "allowed_change_types": ["instruction"],
            "excluded_change_types": ["tool"],
            "risk_ceiling": "low",
            "expires_at": expires_at,
            "reason": "Fast copy fixes for this agent.",
        },
    )
    assert preapproved.status_code == 201, preapproved.text
    assert preapproved.json()["agent_id"] == str(agent_id)
    listed_classes = client.get(
        f"/v1/agents/{agent_id}/pre-approved-classes",
        headers=_auth(),
    )
    assert listed_classes.status_code == 200, listed_classes.text
    assert listed_classes.json()["items"][0]["id"] == preapproved.json()["id"]

    probe = client.post(
        f"/v1/agents/{agent_id}/adversarial-probes/run",
        headers=_auth(),
        json={
            "rule_id": "refund_cap",
            "rule_text": "Never approve refunds over $500.",
            "risk_class": "high",
        },
    )
    assert probe.status_code == 201, probe.text
    catch = probe.json()["catches"][0]
    resolved = client.post(
        f"/v1/agents/{agent_id}/catches/{catch['id']}/resolve",
        headers=_auth(),
        json={
            "intended_interpretation": "Apply the cap cumulatively per conversation.",
            "rejected_interpretation": "Do not split refunds to bypass the cap.",
            "create_eval_cases": True,
        },
    )
    assert resolved.status_code == 200, resolved.text
    assert len(resolved.json()["eval_case_refs"]) == 2

    run = client.post(
        f"/v1/agents/{agent_id}/simulator/runs",
        headers=_auth(),
        json={
            "prompt": "Can I cancel?",
            "final_answer": "I will check policy first.",
            "channel": "web",
            "trace_id": "trace_agent_scoped_simulator",
            "status": "completed",
            "cost_usd": 0.01,
            "latency_ms": 750,
        },
    )
    assert run.status_code == 201, run.text
    assert run.json()["agent_id"] == str(agent_id)
    runs = client.get(f"/v1/agents/{agent_id}/simulator/runs", headers=_auth())
    assert runs.status_code == 200, runs.text
    assert runs.json()["items"][0]["id"] == run.json()["id"]

    repair = client.post(
        f"/v1/agents/{agent_id}/behavior/repair-proposals",
        headers=_auth(),
        json={
            "sentence_id": "sentence_policy",
            "sentence_text": "Cite the current policy before refund windows.",
            "trace_id": "trace_agent_scoped_repair",
            "failure_reason": "Agent cited archived policy.",
            "replay_ref": "replay/agent-scoped-repair",
        },
    )
    assert repair.status_code == 201, repair.text
    assert repair.json()["agent_id"] == str(agent_id)

    observed = client.post(
        f"/v1/agents/{agent_id}/eval-cases/from-observed-failure",
        headers=_auth(),
        json={
            "sentence_id": "sentence_policy",
            "sentence_text": "Cite the current policy before refund windows.",
            "trace_id": "trace_agent_scoped_observed",
            "failure_reason": "Agent cited archived policy.",
            "expected_outcome": "Use the current refund policy and cite it.",
            "proposed_fix": "Tighten the refund policy behavior rule.",
            "replay_ref": "replay/agent-scoped-observed",
        },
    )
    assert observed.status_code == 201, observed.text
    assert observed.json()["case"]["input"]["agent_id"] == str(agent_id)


def test_incident_routes_resolve_workspace_from_agent_id(
    client: TestClient,
) -> None:
    workspace_id = _workspace(client)
    agent_id = _agent(client, workspace_id)
    _approved_change_package(client, agent_id)

    created = client.post(
        f"/v1/agents/{agent_id}/incidents/anomaly",
        headers=_auth(),
        json={
            "severity": "high",
            "trigger": "Refund policy drifted in WhatsApp.",
            "affected_trace_ids": ["trace_incident_agent_scoped"],
            "affected_conversation_count": 1,
            "root_cause_hypothesis": "Draft behavior skipped the latest policy.",
            "proposed_fix": "Require current policy citation before refund answers.",
            "channel_scope": ["whatsapp"],
        },
    )
    assert created.status_code == 201, created.text
    incident = created.json()
    assert incident["workspace_id"] == str(workspace_id)

    listed = client.get(f"/v1/agents/{agent_id}/incidents", headers=_auth())
    assert listed.status_code == 200, listed.text
    assert listed.json()["items"][0]["id"] == incident["id"]

    seeded = client.post(
        f"/v1/agents/{agent_id}/incidents/{incident['id']}/eval-cases",
        headers=_auth(),
    )
    assert seeded.status_code == 201, seeded.text
    assert seeded.json()["case_ids"]

    fix = client.post(
        f"/v1/agents/{agent_id}/incidents/{incident['id']}/change-package",
        headers=_auth(),
        json={
            "summary": "Fix refund drift from incident.",
            "to_version_id": "draft-incident-fix",
        },
    )
    assert fix.status_code == 201, fix.text
    assert fix.json()["incident"]["fix_change_package_id"] == fix.json()["change_package"]["id"]

    resolved = client.post(
        f"/v1/agents/{agent_id}/incidents/{incident['id']}/resolve",
        headers=_auth(),
        json={"note": "Fix package staged and regression eval created."},
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved"


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
