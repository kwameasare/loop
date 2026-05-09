"""Tests for canonical UX wire-up routes."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from loop_control_plane.app import create_app
from loop_control_plane.paseto import encode_local
from loop_control_plane.trace_search import TraceSummary

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
def workspace_id(client: TestClient) -> UUID:
    response = client.post(
        "/v1/workspaces",
        headers={"authorization": _bearer_for("owner-1")},
        json={"name": "Acme", "slug": f"acme-{uuid4().hex[:8]}", "region": "eu-west"},
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


@pytest.fixture
def agent_id(client: TestClient, workspace_id: UUID) -> UUID:
    response = client.post(
        "/v1/agents",
        headers={
            "authorization": _bearer_for("owner-1"),
            "x-loop-workspace-id": str(workspace_id),
        },
        json={"name": "Support Bot", "slug": f"support-{uuid4().hex[:8]}"},
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def _auth(sub: str = "owner-1") -> dict[str, str]:
    return {"authorization": _bearer_for(sub)}


def _add_trace(client: TestClient, workspace_id: UUID, agent_id: UUID, trace_id: str) -> None:
    cp = client.app.state.cp  # type: ignore[attr-defined]
    cp.trace_store.add(
        TraceSummary(
            workspace_id=workspace_id,
            trace_id=trace_id,
            turn_id=uuid4(),
            conversation_id=uuid4(),
            agent_id=agent_id,
            started_at=datetime(2026, 5, 7, 10, 0, tzinfo=UTC),
            duration_ms=180,
            span_count=8,
        )
    )


def _start_live_deployment(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
) -> dict[str, object]:
    package = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "from_version_id": "v1",
            "to_version_id": "v2",
            "summary": "Promote approved canary.",
            "eval_results_ref": "eval/run/v2",
            "replay_results_ref": "replay/run/v2",
            "rollback_target_version_id": "v1",
        },
    ).json()
    submitted = client.post(
        f"/v1/agents/{agent_id}/change-packages/{package['id']}/submit",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert submitted.status_code == 200, submitted.text
    for approval_id in ("owner", "compliance"):
        approved = client.post(
            f"/v1/agents/{agent_id}/change-packages/{package['id']}/approvals",
            headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
            json={"approval_id": approval_id, "decision": "approve"},
        )
        assert approved.status_code == 200, approved.text
    started = client.post(
        f"/v1/agents/{agent_id}/deployments/start",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "change_package_id": package["id"],
            "version_id": "v2",
            "traffic_percent": 10,
            "channel_scope": ["web_chat"],
        },
    )
    assert started.status_code == 201, started.text
    deployment = started.json()["deployment"]
    promoted = client.post(
        f"/v1/agents/{agent_id}/deployments/{deployment['id']}/promote",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert promoted.status_code == 200, promoted.text
    return promoted.json()


def test_presence_websocket_broadcasts_selection_updates(
    client: TestClient, workspace_id: UUID
) -> None:
    url = f"/v1/workspaces/{workspace_id}/presence?caller_sub=owner-1"
    with client.websocket_connect(url) as ws1:
        assert ws1.receive_json()["type"] == "presence.joined"
        with client.websocket_connect(url) as ws2:
            assert ws1.receive_json()["type"] == "presence.joined"
            assert ws2.receive_json()["type"] == "presence.joined"
            ws1.send_json({"type": "selection.update", "cursor": {"x": 42, "y": 8}})
            assert ws1.receive_json()["type"] == "selection.update"
            peer_event = ws2.receive_json()
            assert peer_event["type"] == "selection.update"
            assert peer_event["cursor"] == {"x": 42, "y": 8}


def test_replay_against_draft_and_version_diff_are_audited(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    trace_id = "trace-prod-1"
    response = client.post(
        f"/v1/agents/{agent_id}/replay/against-draft",
        headers=_auth(),
        json={"trace_ids": [trace_id], "draft_branch_ref": "draft/safer-refunds"},
    )
    assert response.status_code == 200, response.text
    row = response.json()["items"][0]
    assert row["trace_id"] == trace_id
    assert row["token_aligned_rows"][1]["status"] == "changed"

    diff = client.post(
        f"/v1/agents/{agent_id}/replay/diff",
        headers=_auth(),
        json={
            "trace_ids": [trace_id],
            "draft_branch_ref": "v23",
            "compare_version_ref": "v22",
        },
    )
    assert diff.status_code == 200, diff.text
    assert diff.json()["items"][0]["baseline_version_ref"] == "v22"

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert {event["action"] for event in audit} >= {
        "replay:against_draft",
        "replay:version_diff",
    }


def test_dashboard_pins_persist_and_homepage_pins_are_user_scoped(
    client: TestClient, workspace_id: UUID
) -> None:
    created = client.post(
        f"/v1/workspaces/{workspace_id}/dashboards",
        headers=_auth(),
        json={
            "name": "Production health",
            "layout": [{"metric_id": "p95_latency", "span": 4}],
            "shared_with": ["teammate@example.com"],
        },
    )
    assert created.status_code == 201, created.text
    listed = client.get(f"/v1/workspaces/{workspace_id}/dashboards", headers=_auth())
    assert listed.json()["items"][0]["layout"][0]["metric_id"] == "p95_latency"

    pin = client.post(
        f"/v1/workspaces/{workspace_id}/homepage/pins",
        headers=_auth(),
        json={
            "source_type": "trace",
            "source_id": "trace-prod-1",
            "title": "Worst trace",
            "href": "/traces/trace-prod-1",
        },
    )
    assert pin.status_code == 201, pin.text
    pins = client.get(f"/v1/workspaces/{workspace_id}/homepage/pins", headers=_auth())
    assert pins.json()["items"][0]["title"] == "Worst trace"


def test_estate_health_derives_claims_from_workspace_objects(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    cp = client.app.state.cp  # type: ignore[attr-defined]
    cp.trace_store.add(
        TraceSummary(
            workspace_id=workspace_id,
            trace_id="4" * 32,
            turn_id=uuid4(),
            conversation_id=uuid4(),
            agent_id=agent_id,
            started_at=datetime(2026, 5, 7, 10, 0, tzinfo=UTC),
            duration_ms=240,
            span_count=5,
            error=True,
        )
    )
    changeset = client.post(
        f"/v1/workspaces/{workspace_id}/approval-changesets",
        headers=_auth(),
        json={"title": "Safer refunds", "payload": {"prompt": "require approval"}},
    )
    assert changeset.status_code == 201, changeset.text

    response = client.get(
        f"/v1/workspaces/{workspace_id}/estate-health",
        headers=_auth(),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data_source"] == "live"
    assert "agents.list_for_workspace" in body["provenance"]
    assert body["summary"]["agents_total"] == 1
    assert body["summary"]["agents_draft"] == 1
    assert body["summary"]["pending_approvals"] == 1
    assert body["summary"]["trace_errors"] == 1
    assert {item["id"] for item in body["attention"]} >= {
        "pending-approvals",
        "trace-errors",
        f"draft-agent-{agent_id}",
    }
    assert all(item["source"] for item in body["attention"])


def test_agent_commitment_contract_can_be_drafted_accepted_and_versioned(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    current = client.get(
        f"/v1/agents/{agent_id}/commitment/current",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert current.status_code == 200, current.text
    assert current.json()["status"] == "draft"
    assert current.json()["version"] == 1
    assert "target_users" in current.json()["structured_summary"]["missing_required_fields"]

    body = {
        "business_responsibility": "Resolve billing cancellation requests safely.",
        "target_users": "Existing enterprise customers and support operators.",
        "owner_user_id": "maya@acme.test",
        "backup_owner_user_id": "diego@acme.test",
        "worst_case_failure": "Incorrectly promises a refund outside policy.",
        "channels": ["web", "whatsapp", "voice"],
        "systems_touched": ["billing", "crm"],
        "regions": ["us-east-1", "eu-west-2"],
        "languages": ["en", "es"],
        "success_metric": "95% eval pass rate before canary.",
        "compliance_domain": "SOC2 support operations",
        "expected_volume": "20k turns per month",
        "launch_date": "2026-06-01",
        "budget_target": "$0.08 per resolved turn",
        "out_of_scope": "Legal advice and payment disputes above $500.",
        "escalation_policy": "Escalate policy conflicts to support lead.",
    }
    drafted = client.post(
        f"/v1/agents/{agent_id}/commitment",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"body": body, "created_from": "studio:new_agent_wizard"},
    )
    assert drafted.status_code == 201, drafted.text
    assert drafted.json()["structured_summary"]["readiness"] == "complete"
    assert drafted.json()["owner_user_id"] == "maya@acme.test"

    accepted = client.post(
        f"/v1/agents/{agent_id}/commitment/accept",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"
    assert accepted.json()["accepted_at"] is not None

    revised = {
        **body,
        "business_responsibility": "Resolve billing and plan-change requests safely.",
    }
    versioned = client.post(
        f"/v1/agents/{agent_id}/commitment",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"body": revised, "created_from": "studio:contract_edit"},
    )
    assert versioned.status_code == 201, versioned.text
    assert versioned.json()["version"] == 2
    assert versioned.json()["status"] == "draft"

    history = client.get(
        f"/v1/agents/{agent_id}/commitments",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert [item["status"] for item in history.json()["items"]] == [
        "superseded",
        "draft",
    ]

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert {event["action"] for event in audit} >= {
        "commitment:draft_save",
        "commitment:accept",
    }


def test_change_package_preflight_links_commitment_evidence_and_stales_on_change(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    package = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "branch_id": "main/draft",
            "change_set_id": "cs_refund",
            "release_candidate_id": "rc_refund_v2",
            "from_version_id": "v1",
            "to_version_id": "v2",
            "target_environment": "production",
            "summary": "Promote safer refund handling to canary.",
            "semantic_diff": [
                {
                    "dimension": "behavior",
                    "summary": "Requires account verification before refund answer.",
                    "evidence_ref": "trace/replay/refund-account-check",
                }
            ],
            "eval_results_ref": "eval/run/refund-v2",
            "replay_results_ref": "replay/run/refund-v2",
            "cost_summary": "+$0.002 per turn estimated.",
            "latency_summary": "+80 ms p95 estimated.",
            "channel_readiness_summary": "Web and WhatsApp ready; voice blocked.",
            "rollback_target_version_id": "v1",
        },
    )
    assert package.status_code == 201, package.text
    body = package.json()
    assert body["status"] == "generated"
    assert body["commitment_document_id"].startswith("commit_")
    assert body["evidence"]["commitment"] == body["commitment_document_id"]
    assert body["required_approvals"][0]["role"] == "Agent owner"

    submitted = client.post(
        f"/v1/agents/{agent_id}/change-packages/{body['id']}/submit",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "submitted"
    assert submitted.json()["submitted_at"] is not None

    owner_approval = client.post(
        f"/v1/agents/{agent_id}/change-packages/{body['id']}/approvals",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"approval_id": "owner", "decision": "approve", "comment": "Owner reviewed."},
    )
    assert owner_approval.status_code == 200, owner_approval.text
    assert owner_approval.json()["status"] == "submitted"
    assert owner_approval.json()["approval_status"] == "partially_approved"
    owner = owner_approval.json()["required_approvals"][0]
    assert owner["content_hash"] == body["content_hash"]
    assert owner["state"] == "approved"

    compliance_approval = client.post(
        f"/v1/agents/{agent_id}/change-packages/{body['id']}/approvals",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "approval_id": "compliance",
            "decision": "approve",
            "comment": "Evidence is sufficient.",
        },
    )
    assert compliance_approval.status_code == 200, compliance_approval.text
    assert compliance_approval.json()["status"] == "approved"
    assert compliance_approval.json()["approval_status"] == "approved"
    assert all(
        approval.get("content_hash") == body["content_hash"]
        for approval in compliance_approval.json()["required_approvals"]
        if approval["required"]
    )

    changed = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "branch_id": "main/draft",
            "change_set_id": "cs_refund",
            "release_candidate_id": "rc_refund_v3",
            "from_version_id": "v1",
            "to_version_id": "v3",
            "summary": "Promote safer refund handling plus Spanish copy.",
        },
    )
    assert changed.status_code == 201, changed.text
    assert changed.json()["id"] != body["id"]

    history = client.get(
        f"/v1/agents/{agent_id}/change-packages",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    ).json()["items"]
    assert [item["status"] for item in history] == ["stale", "generated"]
    assert history[0]["approval_status"] == "stale"
    assert history[0]["required_approvals"][0]["state"] == "invalidated"
    assert history[0]["required_approvals"][0]["satisfied"] is False

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert {event["action"] for event in audit} >= {
        "change_package:generate",
        "change_package:submit",
        "change_package:approval",
    }


def test_channel_bindings_are_peer_agent_objects_with_readiness(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    listed = client.get(
        f"/v1/agents/{agent_id}/channel-bindings",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert listed.status_code == 200, listed.text
    bindings = listed.json()["items"]
    channel_types = {item["channel_type"] for item in bindings}
    assert channel_types == {
        "web_chat",
        "whatsapp",
        "telegram",
        "slack",
        "teams",
        "sms",
        "email",
        "voice",
        "webhook_api",
    }
    assert all(item["readiness"] for item in bindings)
    assert sum(1 for item in bindings if item["channel_type"] == "voice") == 1

    whatsapp = client.post(
        f"/v1/agents/{agent_id}/channel-bindings",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "channel_type": "whatsapp",
            "provider": "Meta Cloud API",
            "display_name": "Acme WhatsApp support",
            "identity_config": {"business_account_id": "waba_123"},
            "auth_config_ref": "secret://channels/whatsapp/acme",
        },
    )
    assert whatsapp.status_code == 201, whatsapp.text
    body = whatsapp.json()
    assert body["status"] == "draft"
    assert body["channel_type"] == "whatsapp"
    assert body["readiness"][0]["status"] == "pending"

    checked = client.post(
        f"/v1/agents/{agent_id}/channel-bindings/{body['id']}/readiness/business_verified",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "status": "passed",
            "evidence_ref": "provider/meta/business/waba_123",
            "message": "Business identity verified by Meta.",
        },
    )
    assert checked.status_code == 200, checked.text
    assert checked.json()["readiness"][0]["status"] == "passed"
    assert checked.json()["readiness"][0]["evidence_ref"] == "provider/meta/business/waba_123"

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert {event["action"] for event in audit} >= {
        "channel_binding:upsert",
        "channel_binding:readiness",
    }


def test_tool_contracts_default_sandbox_promote_live_and_invalidate_on_change(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    contract_body = {
        "name": "issue_refund",
        "description": "Create a refund only after policy and approval checks.",
        "side_effect_level": "money_movement",
        "pii_access": False,
        "money_movement": True,
        "rate_limits": {"per_minute": 20},
        "budget_limits": {"max_per_call_cents": 50_000, "daily_cents": 250_000},
        "sandbox_status": "sandbox",
        "owner_user_id": "maya@acme.test",
        "approval_policy_id": "policy-refund-tool",
        "failure_behavior": "Escalate instead of promising a refund.",
        "compensation_behavior": "Void pending refund when downstream write fails.",
    }
    created = client.put(
        f"/v1/agents/{agent_id}/tool-contracts/issue_refund",
        headers=_auth(),
        json=contract_body,
    )
    assert created.status_code == 200, created.text
    assert created.json()["sandbox_status"] == "sandbox"
    assert created.json()["live_status"] == "disabled"
    assert created.json()["budget_limits"]["max_per_call_cents"] == 50_000

    promoted = client.post(
        f"/v1/agents/{agent_id}/tool-contracts/issue_refund/promote",
        headers=_auth(),
    )
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["live_status"] == "approved"

    changed = client.put(
        f"/v1/agents/{agent_id}/tool-contracts/issue_refund",
        headers=_auth(),
        json={**contract_body, "budget_limits": {"max_per_call_cents": 25_000}},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["live_status"] == "review_required"
    assert changed.json()["approval_invalidated_at"] is not None

    listed = client.get(f"/v1/agents/{agent_id}/tool-contracts", headers=_auth())
    assert listed.status_code == 200, listed.text
    assert listed.json()["items"][0]["tool_id"] == "issue_refund"

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert {event["action"] for event in audit} >= {
        "tool_contract:upsert",
        "tool_contract:promote",
    }


def test_memory_policies_require_trace_backed_privacy_and_invalidate_approval(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    created = client.put(
        f"/v1/agents/{agent_id}/memory-policies/user",
        headers=_auth(),
        json={
            "scope": "user",
            "allowed_memory_types": ["preference", "support_context"],
            "retention": "Keep confirmed preferences for 365 days.",
            "consent_requirement": "Explicit consent required before durable write.",
            "pii_policy": "Do not store payment data; redact personal identifiers.",
            "delete_behavior": "Delete on user request with audit trail.",
            "privacy_implications": [
                "Durable preference affects future conversations for this user.",
                "Every write must link to the source turn.",
            ],
            "source_trace_required": True,
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["scope"] == "user"
    assert body["approval_status"] == "review_required"
    assert body["source_trace_required"] is True
    assert body["privacy_implications"][0].startswith("Durable preference")

    approved = client.post(
        f"/v1/agents/{agent_id}/memory-policies/user/approve",
        headers=_auth(),
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["approval_status"] == "approved"
    assert approved.json()["approval_invalidated_at"] is None

    changed = client.put(
        f"/v1/agents/{agent_id}/memory-policies/user",
        headers=_auth(),
        json={
            "scope": "user",
            "allowed_memory_types": ["preference", "support_context"],
            "retention": "Keep confirmed preferences for 90 days.",
            "consent_requirement": "Explicit consent required before durable write.",
            "pii_policy": "Do not store payment data; redact personal identifiers.",
            "delete_behavior": "Delete on user request with audit trail.",
            "privacy_implications": [
                "Durable preference affects future conversations for this user.",
                "Every write must link to the source turn.",
            ],
            "source_trace_required": True,
        },
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["approval_status"] == "review_required"
    assert changed.json()["approval_invalidated_at"] is not None

    listed = client.get(
        f"/v1/agents/{agent_id}/memory-policies",
        headers=_auth(),
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["items"][0]["retention"].startswith("Keep confirmed")

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert {event["action"] for event in audit} >= {
        "memory_policy:upsert",
        "memory_policy:approve",
    }


def test_deployment_start_creates_evidence_pack_from_approved_change_package(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    package = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "from_version_id": "v1",
            "to_version_id": "v2",
            "summary": "Promote approved web and WhatsApp canary.",
            "eval_results_ref": "eval/run/v2",
            "replay_results_ref": "replay/run/v2",
            "rollback_target_version_id": "v1",
        },
    ).json()
    submitted = client.post(
        f"/v1/agents/{agent_id}/change-packages/{package['id']}/submit",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert submitted.status_code == 200, submitted.text
    for approval_id in ("owner", "compliance"):
        approved = client.post(
            f"/v1/agents/{agent_id}/change-packages/{package['id']}/approvals",
            headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
            json={"approval_id": approval_id, "decision": "approve"},
        )
        assert approved.status_code == 200, approved.text

    start = client.post(
        f"/v1/agents/{agent_id}/deployments/start",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "change_package_id": package["id"],
            "version_id": "v2",
            "traffic_percent": 10,
            "channel_scope": ["web_chat", "whatsapp"],
            "region_scope": ["us-east-1"],
            "auto_rollback_thresholds": {"error_rate": 0.02},
        },
    )
    assert start.status_code == 201, start.text
    deployment = start.json()["deployment"]
    evidence_pack = start.json()["evidence_pack"]
    assert deployment["status"] == "canary"
    assert deployment["trafficPercent"] == 10
    assert deployment["evidencePackId"] == evidence_pack["id"]
    assert evidence_pack["change_package_id"] == package["id"]
    assert evidence_pack["version_manifest"]["content_hash"] == package["content_hash"]

    promoted = client.post(
        f"/v1/agents/{agent_id}/deployments/{deployment['id']}/promote",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["status"] == "live"
    assert promoted.json()["trafficPercent"] == 100

    packs = client.get(
        f"/v1/agents/{agent_id}/evidence-packs",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert packs.status_code == 200, packs.text
    assert packs.json()["items"][0]["id"] == evidence_pack["id"]

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert {event["action"] for event in audit} >= {
        "deployment:start",
        "deployment:promote",
    }


def test_observed_failure_eval_case_closes_90_second_editing_loop(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    response = client.post(
        f"/v1/agents/{agent_id}/eval-cases/from-observed-failure",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "sentence_id": "sentence_purpose_cancel",
            "sentence_text": "When a customer asks to cancel, cite May 2026 policy.",
            "trace_id": "trace_refund_742",
            "failure_reason": ("Agent cited archived policy before current May 2026 policy."),
            "expected_outcome": ("Cite the May 2026 refund policy before quoting refund window."),
            "proposed_fix": (
                "Add a behavior rule requiring current policy citation before refund windows."
            ),
            "replay_ref": "replay/run/trace_refund_742/fixed",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["suite_id"]
    assert body["case_id"]
    assert body["case"]["source"] == "behavior-fix"
    assert body["case"]["source_ref"] == "trace_refund_742"
    assert body["case"]["input"]["sentence_id"] == "sentence_purpose_cancel"
    assert body["case"]["expected"]["proposed_fix"].startswith("Add a behavior rule")
    assert body["case"]["scorers"][1]["kind"] == "trace_regression"

    suites = client.get(
        f"/v1/workspaces/{workspace_id}/eval-suites",
        headers=_auth(),
    )
    assert suites.status_code == 200, suites.text
    assert "Observed behavior failures" in {item["name"] for item in suites.json()["items"]}

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert "eval:case:create_from_observed_failure" in {event["action"] for event in audit}


def test_incident_response_links_auto_rollback_and_seeds_eval_cases(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    live = _start_live_deployment(client, workspace_id, agent_id)
    _add_trace(client, workspace_id, agent_id, "5" * 32)

    rolled_back = client.post(
        f"/v1/agents/{agent_id}/deployments/{live['id']}/rollback",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "mode": "auto",
            "trigger": "error_rate breached 4% for web_chat canary",
            "reason": "Tool schema changed upstream and increased failures.",
        },
    )
    assert rolled_back.status_code == 200, rolled_back.text
    assert rolled_back.json()["status"] == "rolled_back"

    listed = client.get(
        f"/v1/agents/{agent_id}/incidents",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert listed.status_code == 200, listed.text
    incident = listed.json()["items"][0]
    assert incident["status"] == "contained"
    assert incident["deployment_id"] == live["id"]
    assert incident["rollback_action_ref"] == f"deployment/{live['id']}/rollback"
    assert incident["report"]["suspected_cause"].startswith("Tool schema")
    assert incident["report"]["rollback_status"] == "executed"

    seeded = client.post(
        f"/v1/agents/{agent_id}/incidents/{incident['id']}/eval-cases",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert seeded.status_code == 201, seeded.text
    assert seeded.json()["ok"] is True
    assert seeded.json()["suite_id"]
    assert seeded.json()["case_ids"]
    assert seeded.json()["incident"]["candidate_eval_suite_id"] == seeded.json()["suite_id"]

    workspace_incidents = client.get(
        f"/v1/workspaces/{workspace_id}/incidents",
        headers=_auth(),
    )
    assert workspace_incidents.status_code == 200, workspace_incidents.text
    assert workspace_incidents.json()["items"][0]["id"] == incident["id"]

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert {event["action"] for event in audit} >= {
        "deployment:rollback",
        "incident:create_auto_rollback",
        "incident:eval_cases_seeded",
    }


def test_comment_resolution_can_create_eval_case(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    response = client.post(
        f"/v1/agents/{agent_id}/comments/cmt_123/resolve",
        headers=_auth(),
        json={
            "expected_behavior": "Refund premium customers immediately.",
            "failure_reason": "Agent escalated instead of refunding.",
            "source_trace": "trace-prod-1",
            "also_create_eval_case": True,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["case_id"] == "eval_comment_cmt_123"


def test_approval_edit_invalidates_content_hash_bound_approval(
    client: TestClient, workspace_id: UUID
) -> None:
    changeset = client.post(
        f"/v1/workspaces/{workspace_id}/approval-changesets",
        headers=_auth(),
        json={"title": "Raise tool budget", "payload": {"budget_usd": 10}},
    ).json()
    approved = client.post(
        f"/v1/workspaces/{workspace_id}/approval-changesets/{changeset['id']}/approve",
        headers=_auth(),
    ).json()
    assert approved["approvals"][0]["state"] == "approved"

    edited = client.post(
        f"/v1/workspaces/{workspace_id}/approval-changesets/{changeset['id']}/edit",
        headers=_auth(),
        json={"title": "Raise tool budget", "payload": {"budget_usd": 20}},
    )
    assert edited.status_code == 200, edited.text
    body = edited.json()
    assert body["approvals"] == []
    assert body["invalidated_approvals"][0]["state"] == "invalidated"


def test_byok_rotation_revocation_and_residency_block_are_audited(
    client: TestClient, workspace_id: UUID
) -> None:
    bind = client.post(
        f"/v1/workspaces/{workspace_id}/encryption/key",
        headers=_auth(),
        json={
            "provider": "aws-kms",
            "key_uri": "arn:aws:kms:eu-west-2:111:key/abc",
            "role_binding": "arn:aws:iam::111:role/loop",
        },
    )
    assert bind.status_code == 200, bind.text
    rotate = client.post(
        f"/v1/workspaces/{workspace_id}/encryption/key/rotate",
        headers=_auth(),
    ).json()
    assert rotate["version"] == 2
    revoke = client.post(
        f"/v1/workspaces/{workspace_id}/encryption/key/revoke",
        headers=_auth(),
    ).json()
    assert revoke["workspace_disabled"] is True
    assert revoke["status"] == "revoked"

    residency = client.post(
        f"/v1/workspaces/{workspace_id}/residency/check",
        headers=_auth(),
        json={"target_region": "na-east", "tool_name": "lookup_order"},
    )
    assert residency.status_code == 200, residency.text
    assert residency.json()["code"] == "LOOP-AC-602"
    assert residency.json()["trace_event"] == "cross_region_blocked"


def test_behavior_telemetry_inverse_retrieval_voice_and_scenes(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    trace_id = "2" * 32
    _add_trace(client, workspace_id, agent_id, trace_id)

    telemetry = client.get(
        f"/v1/agents/{agent_id}/behavior/sentence-telemetry",
        headers=_auth(),
    )
    assert telemetry.status_code == 200, telemetry.text
    assert telemetry.json()["items"][0]["representative_traces"] == [trace_id]

    inverse = client.post(
        f"/v1/agents/{agent_id}/kb/inverse-retrieval",
        headers=_auth(),
        json={"chunk_id": "chunk_refunds"},
    )
    assert inverse.status_code == 200, inverse.text
    assert inverse.json()["items"][0]["trace_id"] == trace_id

    number = client.post(
        f"/v1/workspaces/{workspace_id}/voice/numbers/provision",
        headers=_auth(),
        json={"country": "US", "area_code": "415", "capability": "voice", "provider": "twilio"},
    )
    assert number.status_code == 200, number.text
    assert number.json()["provisioner"] == "deterministic"
    assert number.json()["sip_route"].startswith("livekit://")

    scorers = client.get("/v1/eval-scorers/voice", headers=_auth()).json()["items"]
    assert {item["id"] for item in scorers} >= {"voice_wer", "voice_stage_latency"}

    scene = client.post(
        f"/v1/workspaces/{workspace_id}/scenes",
        headers=_auth(),
        json={
            "name": "Refund escalation",
            "category": "refund flow",
            "trace_ids": [trace_id],
            "expected_behavior": "Refund or explain policy.",
        },
    )
    assert scene.status_code == 201, scene.text
    replay = client.post(
        f"/v1/workspaces/{workspace_id}/scenes/{scene.json()['id']}/replay",
        headers=_auth(),
    )
    assert replay.json()["trace_ids"] == [trace_id]


def test_tool_import_persona_semantic_diff_style_bisect_and_shares(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    client.post(
        f"/v1/agents/{agent_id}/versions",
        headers=_auth(),
        json={"spec": {"prompt": "Keep answers under 100 words."}, "notes": "tightened copy"},
    )

    tool = client.post(
        f"/v1/agents/{agent_id}/tools/import",
        headers=_auth(),
        json={"source": "curl -X POST https://api.stripe.com/v1/customers", "source_kind": "curl"},
    )
    assert tool.status_code == 200, tool.text
    assert tool.json()["name"] == "stripe_request"
    assert tool.json()["safety_contract"]["approval_required"] is True

    persona = client.post(
        f"/v1/agents/{agent_id}/persona-test",
        headers=_auth(),
        json={"persona_set": "first-user"},
    )
    assert len(persona.json()["items"]) == 5

    latency = client.post(
        f"/v1/agents/{agent_id}/latency-budget",
        headers=_auth(),
        json={"trace_id": "trace-prod-1", "target_latency_ms": 900},
    )
    assert latency.status_code == 200, latency.text
    assert latency.json()["suggestions"][0]["saves_ms"] > 0

    ablation = client.post(
        f"/v1/agents/{agent_id}/context-ablation",
        headers=_auth(),
        json={"turn_id": "turn-1", "toggles": {"prompt_sections": False}},
    )
    assert ablation.status_code == 200, ablation.text
    assert ablation.json()["items"][0]["id"] == "prompt_sections"
    assert ablation.json()["items"][0]["cost_delta_pct"] < 0

    empty = client.get(
        f"/v1/agents/{agent_id}/empty-state-suggestions?surface=evals",
        headers=_auth(),
    )
    assert empty.status_code == 200, empty.text
    assert "starter eval suite" in empty.json()["items"][0]["title"]

    semantic = client.post(
        f"/v1/agents/{agent_id}/semantic-diff",
        headers=_auth(),
        json={"before": "Keep under 100 words.", "after": "Refuse medical advice."},
    )
    summaries = [item["summary"] for item in semantic.json()["items"]]
    assert any("100 words" in summary for summary in summaries)
    assert any("medical advice" in summary for summary in summaries)

    style = client.post(
        f"/v1/agents/{agent_id}/style-transfer",
        headers=_auth(),
        json={"section": "Be clear."},
    )
    assert {item["voice"] for item in style.json()["items"]} == {
        "formal",
        "casual",
        "empathetic",
        "concise",
        "expert",
    }

    bisect = client.post(
        f"/v1/agents/{agent_id}/bisect",
        headers=_auth(),
        json={"failing_eval_case_id": "eval.refund.regressed"},
    )
    assert bisect.json()["status"] == "complete"

    share = client.post(
        f"/v1/workspaces/{workspace_id}/shares",
        headers=_auth(),
        json={
            "source_type": "trace",
            "source_id": "2" * 32,
            "redactions": ["pii", "secrets"],
        },
    )
    assert share.status_code == 201, share.text
    viewed = client.get(f"/v1/shares/{share.json()['id']}", headers=_auth())
    assert viewed.json()["redaction_banner"].startswith("2 redaction")


def test_pair_debug_audio_and_voice_provisioner_modes(
    client: TestClient,
    workspace_id: UUID,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = client.post(
        f"/v1/workspaces/{workspace_id}/pair-debug/audio/session",
        headers=_auth(),
        json={"agent_id": "agent_support", "participant_id": "builder:peer"},
    )
    assert session.status_code == 200, session.text
    assert session.json()["transport"] == "webrtc"
    assert session.json()["signaling_url"].startswith("wss://")

    monkeypatch.setenv("LOOP_VOICE_PROVISIONER", "twilio")
    for name in [
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
    ]:
        monkeypatch.delenv(name, raising=False)
    blocked = client.post(
        f"/v1/workspaces/{workspace_id}/voice/numbers/provision",
        headers=_auth(),
        json={
            "country": "US",
            "area_code": "415",
            "capability": "voice",
            "provider": "twilio",
        },
    )
    assert blocked.status_code == 503, blocked.text
    assert "Twilio and LiveKit credentials" in blocked.json()["detail"]


def test_telemetry_help_branding_voice_demo_and_activity(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    consent = client.get(
        f"/v1/workspaces/{workspace_id}/telemetry-consent",
        headers=_auth(),
    )
    assert consent.json()["annual_review_due"] is True
    saved = client.post(
        f"/v1/workspaces/{workspace_id}/telemetry-consent",
        headers=_auth(),
        json={
            "product_analytics": False,
            "diagnostics": True,
            "ai_improvement": False,
            "crash_reports": False,
        },
    )
    assert saved.json()["product_analytics"] is False
    assert saved.json()["annual_review_due"] is False

    clips = client.get("/v1/help-clips?surface=pipeline", headers=_auth()).json()["items"]
    assert clips[0]["clip_id"] == "clip_canary_slider"

    branding = client.post(
        f"/v1/workspaces/{workspace_id}/branding/compile",
        headers=_auth(),
        json={
            "logo_url": "https://example.com/logo.png",
            "primary_color": "#123456",
            "custom_domain": "studio.acme.test",
        },
    )
    assert branding.json()["css_variables"]["--loop-brand-primary"] == "#123456"

    demo = client.post(
        f"/v1/workspaces/{workspace_id}/voice/demo-links",
        headers=_auth(),
        json={"snapshot_id": "snap_123", "expires_in_minutes": 5},
    )
    assert demo.status_code == 201, demo.text
    assert demo.json()["url"].startswith("/voice-demo/")

    _add_trace(client, workspace_id, agent_id, "3" * 32)
    activity = client.get(f"/v1/workspaces/{workspace_id}/activity", headers=_auth())
    assert activity.json()["turn_rate_per_minute"] == 1
