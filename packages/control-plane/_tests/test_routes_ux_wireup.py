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


def _mark_channel_ready(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
    channel_type: str,
) -> dict[str, object]:
    created = client.post(
        f"/v1/agents/{agent_id}/channel-bindings",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "channel_type": channel_type,
            "provider": f"{channel_type} provider",
            "display_name": f"Acme {channel_type}",
            "identity_config": {"external_ref": f"{channel_type}_acct"},
            "auth_config_ref": f"secret://channels/{channel_type}/acme",
        },
    )
    assert created.status_code == 201, created.text
    binding = created.json()
    for check in binding["readiness"]:
        updated = client.post(
            f"/v1/agents/{agent_id}/channel-bindings/{binding['id']}/readiness/{check['id']}",
            headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
            json={
                "status": "passed",
                "evidence_ref": f"provider/{channel_type}/{check['id']}",
                "message": f"{check['label']} passed.",
            },
        )
        assert updated.status_code == 200, updated.text
        binding = updated.json()
    assert binding["status"] == "ready"
    return binding


def _complete_commitment_body() -> dict[str, object]:
    return {
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


def _start_live_deployment(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
) -> dict[str, object]:
    _mark_channel_ready(client, workspace_id, agent_id, "web_chat")
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


def _start_canary_deployment(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
    *,
    thresholds: dict[str, float] | None = None,
) -> dict[str, object]:
    _mark_channel_ready(client, workspace_id, agent_id, "web_chat")
    package = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "from_version_id": "v1",
            "to_version_id": "v2",
            "summary": "Canary approved draft with rollout policy.",
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
            "auto_rollback_thresholds": thresholds or {"error_rate": 0.02},
        },
    )
    assert started.status_code == 201, started.text
    return started.json()["deployment"]


def _create_deployable_release_candidate(
    client: TestClient,
    agent_id: UUID,
    *,
    name: str = "Release candidate change set",
) -> dict[str, object]:
    branch = client.post(
        f"/v1/agents/{agent_id}/branches",
        headers=_auth(),
        json={"name": f"{name.lower().replace(' ', '-')}", "base_version_id": "v1"},
    )
    assert branch.status_code == 201, branch.text
    change_set = client.post(
        f"/v1/agents/{agent_id}/change-sets",
        headers=_auth(),
        json={
            "branch_id": branch.json()["id"],
            "name": name,
            "summary": "Prepare governed release candidate for preflight.",
            "source_type": "manual_edit",
            "source_refs": ["trace/replay/refund-account-check"],
            "changed_objects": [
                {
                    "type": "behavior",
                    "id": "behavior.refund_policy",
                    "summary": "Require account verification before refund answer.",
                }
            ],
        },
    )
    assert change_set.status_code == 201, change_set.text
    ready_for_tests = client.post(
        f"/v1/agents/{agent_id}/change-sets/{change_set.json()['id']}/ready-for-tests",
        headers=_auth(),
    )
    assert ready_for_tests.status_code == 200, ready_for_tests.text
    ready_for_review = client.post(
        f"/v1/agents/{agent_id}/change-sets/{change_set.json()['id']}/ready-for-review",
        headers=_auth(),
        json={
            "eval_results_ref": "eval/run/refund-core/green",
            "required_eval_suites": ["refund-core"],
            "passed": True,
        },
    )
    assert ready_for_review.status_code == 200, ready_for_review.text
    rc = client.post(
        f"/v1/agents/{agent_id}/change-sets/{change_set.json()['id']}/release-candidates",
        headers=_auth(),
        json={"required_eval_suites": ["refund-core"], "required_approvals": ["owner"]},
    )
    assert rc.status_code == 201, rc.text
    approved = client.post(
        f"/v1/agents/{agent_id}/release-candidates/{rc.json()['id']}/approve",
        headers=_auth(),
        json={"approval_id": "owner", "comment": "Preflight-ready."},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "deployable"
    return approved.json()


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


def test_replay_frame_fork_and_eval_case_preserve_trace_provenance(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    forked = client.post(
        f"/v1/agents/{agent_id}/replay/forks",
        headers=_auth(),
        json={
            "trace_id": "trace-prod-1",
            "frame_id": "answer-frame",
            "source_version_ref": "v23.1.4",
            "snapshot_id": "snap-prod",
            "evidence_ref": "trace-prod-1/answer-frame",
            "purpose": "Investigate legal escalation replay frame.",
        },
    )
    assert forked.status_code == 201, forked.text
    fork_body = forked.json()
    assert fork_body["branch"]["base_version_id"] == "v23.1.4"
    assert fork_body["change_set"]["source_type"] == "trace_replay_frame"
    assert "trace-prod-1" in fork_body["change_set"]["source_refs"]
    assert fork_body["next_url"].endswith(f"branch_id={fork_body['branch']['id']}")

    eval_case = client.post(
        f"/v1/agents/{agent_id}/replay/eval-cases",
        headers=_auth(),
        json={
            "title": "Legal threat replay regression",
            "trace_id": "trace-prod-1",
            "frame_id": "answer-frame",
            "source_version_ref": "v23.1.4",
            "draft_branch_ref": "draft/refund-clarity",
            "channel": "whatsapp",
            "snapshot_id": "snap-prod",
            "expected_behavior": "Escalate legal threats before answering refund policy.",
            "failure_reason": "Draft missed attorney synonym under replay.",
            "replay_ref": "trace-prod-1/against-draft/answer-frame",
            "risk_tags": ["production-replay", "high", "whatsapp"],
        },
    )
    assert eval_case.status_code == 201, eval_case.text
    eval_body = eval_case.json()
    assert eval_body["suite_id"]
    assert eval_body["case_id"]
    assert eval_body["case"]["source"] == "production-replay"
    assert eval_body["case"]["source_ref"] == "trace-prod-1"
    assert "snap-prod" in eval_body["evidence_refs"]

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert {event["action"] for event in audit} >= {
        "replay:fork_from_frame",
        "replay:eval_case_create",
    }


def test_empty_state_suggestion_acceptance_creates_real_artifacts(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    empty_before = client.get(
        f"/v1/agents/{agent_id}/empty-state-suggestions?surface=evals",
        headers=_auth(),
    )
    assert empty_before.status_code == 200, empty_before.text
    assert empty_before.json()["items"][0]["id"] == "collect_first_proof_traces"

    blocked = client.post(
        f"/v1/agents/{agent_id}/empty-state-suggestions/starter_eval_from_traces/accept",
        headers=_auth(),
        json={"surface": "evals"},
    )
    assert blocked.status_code == 409, blocked.text
    assert "no traces available" in blocked.text

    _add_trace(client, workspace_id, agent_id, "a" * 32)
    _add_trace(client, workspace_id, agent_id, "b" * 32)
    empty_after = client.get(
        f"/v1/agents/{agent_id}/empty-state-suggestions?surface=evals",
        headers=_auth(),
    )
    assert empty_after.status_code == 200, empty_after.text
    assert empty_after.json()["items"][0]["id"] == "starter_eval_from_traces"

    accepted = client.post(
        f"/v1/agents/{agent_id}/empty-state-suggestions/starter_eval_from_traces/accept",
        headers=_auth(),
        json={"surface": "evals"},
    )
    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["ok"] is True
    assert body["title"] == "Created starter eval suite with 2 case(s)."
    assert body["created_refs"][0].startswith("eval-suite/")
    assert len([ref for ref in body["created_refs"] if ref.startswith("eval/")]) == 2
    assert body["next_url"].startswith(f"/agents/{agent_id}/evals?suite_id=")

    suite_id = body["created_refs"][0].split("/", 1)[1]
    cases = client.get(f"/v1/eval-suites/{suite_id}/cases", headers=_auth())
    assert cases.status_code == 200, cases.text
    rows = cases.json()["items"]
    assert len(rows) == 2
    assert {row["source"] for row in rows} == {"empty-state-suggestion"}
    assert {row["input"]["trace_id"] for row in rows} == {"a" * 32, "b" * 32}

    kb_task = client.post(
        f"/v1/agents/{agent_id}/empty-state-suggestions/kb_gap_review/accept",
        headers=_auth(),
        json={"surface": "kb"},
    )
    assert kb_task.status_code == 200, kb_task.text
    assert kb_task.json()["created_refs"][0].startswith("task/")
    assert kb_task.json()["next_url"] == f"/agents/{agent_id}/kb"

    inbox_task = client.post(
        f"/v1/agents/{agent_id}/empty-state-suggestions/seed_inbox_runbook/accept",
        headers=_auth(),
        json={"surface": "inbox"},
    )
    assert inbox_task.status_code == 200, inbox_task.text
    assert inbox_task.json()["next_url"] == f"/inbox?agent_id={agent_id}"

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert "empty_state:suggestion_accept" in {event["action"] for event in audit}


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
    tool = client.put(
        f"/v1/agents/{agent_id}/tool-contracts/refund_payment",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "name": "Refund payment",
            "side_effect_level": "money_movement",
            "pii_access": True,
            "money_movement": True,
            "sandbox_status": "sandbox",
            "owner_user_id": "finance@acme",
            "failure_behavior": "Escalate failed refunds.",
            "compensation_behavior": "",
        },
    )
    assert tool.status_code == 200, tool.text
    channel = client.post(
        f"/v1/agents/{agent_id}/channel-bindings",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "channel_type": "whatsapp",
            "provider": "Meta Cloud API",
            "display_name": "WhatsApp support",
            "status": "draft",
        },
    )
    assert channel.status_code == 201, channel.text
    incident = client.post(
        f"/v1/agents/{agent_id}/incidents/anomaly",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
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
    _mark_channel_ready(client, workspace_id, agent_id, "web_chat")
    package = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "from_version_id": "v1",
            "to_version_id": "v2",
            "summary": "Promote canary for estate visibility.",
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
    deployment = client.post(
        f"/v1/agents/{agent_id}/deployments/start",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "change_package_id": package["id"],
            "version_id": "v2",
            "traffic_percent": 10,
            "channel_scope": ["web_chat"],
            "region_scope": ["eu-west-2"],
            "segment_scope": ["enterprise"],
            "hold_time_minutes": 45,
            "auto_rollback_thresholds": {"error_rate_percent": 2},
        },
    )
    assert deployment.status_code == 201, deployment.text
    catch_run = client.post(
        f"/v1/agents/{agent_id}/adversarial-probes/run",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "rule_id": "refund_cap",
            "rule_text": "Never approve refunds over $500.",
            "risk_class": "high",
        },
    )
    assert catch_run.status_code == 201, catch_run.text

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
    assert body["summary"]["open_incidents"] == 1
    assert body["summary"]["owner_risks"] == 1
    assert body["summary"]["active_rollouts"] == 1
    assert body["summary"]["open_catches"] == 1
    assert "deployments.list_for_agent" in body["provenance"]
    assert "adversarial_catches.list_for_agent" in body["provenance"]
    assert {item["id"] for item in body["attention"]} >= {
        "pending-approvals",
        "trace-errors",
        "open-incidents",
        "continuity-owner-risks",
        f"draft-agent-{agent_id}",
        "active-rollouts",
        "open-adversarial-catches",
    }
    assert all(item["source"] for item in body["attention"])
    catch_attention = next(
        item for item in body["attention"] if item["id"] == "open-adversarial-catches"
    )
    assert f"/agents/{agent_id}/behavior" in catch_attention["href"]
    assert "sentence_id=refund_cap" in catch_attention["href"]
    assert "catch_id=catch_" in catch_attention["href"]
    assert body["shared_dependencies"][0]["id"] == "tool:refund_payment"
    assert body["rollout_health"][0]["status"] == "canary"
    assert body["rollout_health"][0]["traffic_percent"] == 10
    assert body["rollout_health"][0]["channel_scope"] == ["web_chat"]
    assert body["rollout_health"][0]["region_scope"] == ["eu-west-2"]
    assert body["rollout_health"][0]["segment_scope"] == ["enterprise"]
    assert body["rollout_health"][0]["evidence_ref"].startswith("deployment/")
    assert {item["channel_type"] for item in body["channel_health"]} >= {
        "web_chat",
        "whatsapp",
    }
    assert {cluster["kind"] for cluster in body["failure_clusters"]} >= {
        "incident",
        "adversarial_catch",
    }
    catch_cluster = next(
        cluster
        for cluster in body["failure_clusters"]
        if cluster["kind"] == "adversarial_catch"
    )
    assert "sentence_id=refund_cap" in catch_cluster["href"]
    assert "catch_id=catch_" in catch_cluster["href"]
    assert body["owner_risks"][0]["id"] == f"ownerless-agent-{agent_id}"
    assert {
        "cluster_failures",
        "detect_drift",
        "detect_dead_behavior_sections",
        "adversarial_probe_catches",
        "summarize_operator_takeovers",
    } <= {job["id"] for job in body["background_jobs"]}


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

    body = _complete_commitment_body()
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


def test_agent_detail_exposes_durable_object_state_transitions(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    initial = client.get(
        f"/v1/agents/{agent_id}",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert initial.status_code == 200, initial.text
    assert initial.json()["object_state"] == "draft"
    assert initial.json()["state_evidence_ref"].startswith("commitment/")

    drafted = client.post(
        f"/v1/agents/{agent_id}/commitment",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"body": _complete_commitment_body(), "created_from": "studio:new_agent"},
    )
    assert drafted.status_code == 201, drafted.text
    accepted = client.post(
        f"/v1/agents/{agent_id}/commitment/accept",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert accepted.status_code == 200, accepted.text

    saved = client.get(
        f"/v1/agents/{agent_id}",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["object_state"] == "saved"
    assert saved.json()["state_evidence_ref"] == f"commitment/{accepted.json()['id']}"

    package = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "from_version_id": "v1",
            "to_version_id": "v2",
            "summary": "Stage approved canary.",
            "eval_results_ref": "eval/run/v2",
            "replay_results_ref": "replay/run/v2",
            "rollback_target_version_id": "v1",
        },
    )
    assert package.status_code == 201, package.text
    submitted = client.post(
        f"/v1/agents/{agent_id}/change-packages/{package.json()['id']}/submit",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert submitted.status_code == 200, submitted.text

    staged = client.get(
        f"/v1/agents/{agent_id}",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert staged.status_code == 200, staged.text
    assert staged.json()["object_state"] == "staged"
    assert staged.json()["state_evidence_ref"] == f"change_package/{package.json()['id']}"

    for approval_id in ("owner", "compliance"):
        approved = client.post(
            f"/v1/agents/{agent_id}/change-packages/{package.json()['id']}/approvals",
            headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
            json={"approval_id": approval_id, "decision": "approve"},
        )
        assert approved.status_code == 200, approved.text
    _mark_channel_ready(client, workspace_id, agent_id, "web_chat")
    started = client.post(
        f"/v1/agents/{agent_id}/deployments/start",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "change_package_id": package.json()["id"],
            "version_id": "v2",
            "traffic_percent": 10,
            "channel_scope": ["web_chat"],
        },
    )
    assert started.status_code == 201, started.text
    deployment = started.json()["deployment"]

    canary = client.get(
        f"/v1/agents/{agent_id}",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert canary.status_code == 200, canary.text
    assert canary.json()["object_state"] == "canary"
    assert canary.json()["state_evidence_ref"] == f"deployment/{deployment['id']}"

    promoted = client.post(
        f"/v1/agents/{agent_id}/deployments/{deployment['id']}/promote",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert promoted.status_code == 200, promoted.text
    production = client.get(
        f"/v1/agents/{agent_id}",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert production.status_code == 200, production.text
    assert production.json()["object_state"] == "production"

    rolled_back = client.post(
        f"/v1/agents/{agent_id}/deployments/{deployment['id']}/rollback",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert rolled_back.status_code == 200, rolled_back.text
    rollback_state = client.get(
        f"/v1/agents/{agent_id}",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert rollback_state.status_code == 200, rollback_state.text
    assert rollback_state.json()["object_state"] == "rolled_back"


def test_support_agent_mvp_journey_links_trace_eval_deploy_rollback_and_incident(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    drafted = client.post(
        f"/v1/agents/{agent_id}/commitment",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"body": _complete_commitment_body(), "created_from": "mvp_journey"},
    )
    assert drafted.status_code == 201, drafted.text
    accepted = client.post(
        f"/v1/agents/{agent_id}/commitment/accept",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert accepted.status_code == 200, accepted.text
    channel = _mark_channel_ready(client, workspace_id, agent_id, "web_chat")

    simulator_run = client.post(
        f"/v1/agents/{agent_id}/simulator/runs",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "prompt": "Can I cancel my annual renewal?",
            "final_answer": "I will check the current refund policy first.",
            "channel": "web",
            "trace_id": "support_journey_trace",
            "config": {
                "model_alias": "fast-draft",
                "memory_mode": "snapshot",
                "tool_mode": "mock",
            },
            "status": "completed",
            "cost_usd": 0.041,
            "latency_ms": 940,
        },
    )
    assert simulator_run.status_code == 201, simulator_run.text
    trace_id = simulator_run.json()["trace_id"]
    assert simulator_run.json()["channel_binding_id"] == channel["id"]

    eval_case = client.post(
        f"/v1/agents/{agent_id}/eval-cases/from-observed-failure",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "sentence_id": "sentence_cancel_policy",
            "sentence_text": "I can cancel your renewal.",
            "trace_id": trace_id,
            "failure_reason": "Agent answered before checking current policy.",
            "expected_outcome": "Check current policy before quoting cancellation terms.",
            "proposed_fix": "Require current-policy lookup before renewal answers.",
            "replay_ref": f"replay/{trace_id}/draft-fix",
        },
    )
    assert eval_case.status_code == 201, eval_case.text
    assert eval_case.json()["case"]["source_ref"] == trace_id

    release_candidate = _create_deployable_release_candidate(
        client,
        agent_id,
        name="Support journey release candidate",
    )
    package = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "release_candidate_id": release_candidate["id"],
            "from_version_id": "v1",
            "to_version_id": "v2",
            "target_environment": "production",
            "summary": "Promote cancellation support policy fix.",
            "semantic_diff": [
                {
                    "dimension": "behavior",
                    "summary": "Requires current-policy lookup before cancellation answer.",
                    "evidence_ref": f"trace/{trace_id}",
                }
            ],
            "eval_results_ref": f"eval/{eval_case.json()['case_id']}",
            "replay_results_ref": f"replay/{trace_id}/draft-fix",
            "rollback_target_version_id": "v1",
        },
    )
    assert package.status_code == 201, package.text
    package_body = package.json()
    assert package_body["release_candidate_id"] == release_candidate["id"]
    assert package_body["evidence"]["release_candidate"] == release_candidate["id"]

    submitted = client.post(
        f"/v1/agents/{agent_id}/change-packages/{package_body['id']}/submit",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert submitted.status_code == 200, submitted.text
    for approval_id in ("owner", "compliance"):
        approved = client.post(
            f"/v1/agents/{agent_id}/change-packages/{package_body['id']}/approvals",
            headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
            json={"approval_id": approval_id, "decision": "approve"},
        )
        assert approved.status_code == 200, approved.text

    started = client.post(
        f"/v1/agents/{agent_id}/deployments/start",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "change_package_id": package_body["id"],
            "version_id": "v2",
            "traffic_percent": 10,
            "channel_scope": ["web_chat"],
            "auto_rollback_thresholds": {"error_rate": 0.02},
        },
    )
    assert started.status_code == 201, started.text
    deployment = started.json()["deployment"]
    evidence_pack = started.json()["evidence_pack"]
    assert evidence_pack["change_package_id"] == package_body["id"]
    assert evidence_pack["version_manifest"]["release_candidate_id"] == release_candidate["id"]

    evaluated = client.post(
        f"/v1/agents/{agent_id}/deployments/{deployment['id']}/thresholds/evaluate",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "metric": "error_rate",
            "observed": 0.04,
            "policy": "rollback",
            "window": "5m",
            "reason": "Support journey canary exceeded error budget.",
        },
    )
    assert evaluated.status_code == 200, evaluated.text
    assert evaluated.json()["decision"] == "rolled_back"

    incidents = client.get(
        f"/v1/agents/{agent_id}/incidents",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert incidents.status_code == 200, incidents.text
    incident = incidents.json()["items"][0]
    assert incident["deployment_id"] == deployment["id"]
    assert incident["affected_trace_ids"] == [trace_id]
    seeded = client.post(
        f"/v1/agents/{agent_id}/incidents/{incident['id']}/eval-cases",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert seeded.status_code == 201, seeded.text
    assert seeded.json()["incident"]["candidate_eval_suite_id"]

    agent = client.get(
        f"/v1/agents/{agent_id}",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert agent.status_code == 200, agent.text
    assert agent.json()["object_state"] == "rolled_back"
    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert {event["action"] for event in audit} >= {
        "commitment:accept",
        "simulator_run:create",
        "eval:case:create_from_observed_failure",
        "change_package:generate",
        "change_package:approval",
        "deployment:start",
        "deployment:threshold_breach",
        "deployment:rollback",
        "incident:create_auto_rollback",
        "incident:eval_cases_seeded",
    }


def test_branch_change_set_and_release_candidate_state_machine(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    branch = client.post(
        f"/v1/agents/{agent_id}/branches",
        headers=_auth(),
        json={"name": "refund-policy-fix", "base_version_id": "v12"},
    )
    assert branch.status_code == 201, branch.text
    branch_body = branch.json()
    assert branch_body["status"] == "active"
    assert branch_body["base_version_id"] == "v12"

    change_set = client.post(
        f"/v1/agents/{agent_id}/change-sets",
        headers=_auth(),
        json={
            "branch_id": branch_body["id"],
            "name": "Use current refund policy",
            "summary": "Fix archived policy citation on cancellation requests.",
            "source_type": "failed_eval",
            "source_refs": ["eval/refund/current-policy"],
            "changed_objects": [
                {
                    "type": "behavior",
                    "id": "behavior.refund_policy",
                    "summary": "Cite May 2026 policy before refund window.",
                }
            ],
        },
    )
    assert change_set.status_code == 201, change_set.text
    cs_body = change_set.json()
    assert cs_body["status"] == "draft"
    assert cs_body["source_refs"] == ["eval/refund/current-policy"]

    premature = client.post(
        f"/v1/agents/{agent_id}/change-sets/{cs_body['id']}/release-candidates",
        headers=_auth(),
        json={"required_eval_suites": ["refund-core"], "required_approvals": ["owner"]},
    )
    assert premature.status_code == 400, premature.text

    ready_for_tests = client.post(
        f"/v1/agents/{agent_id}/change-sets/{cs_body['id']}/ready-for-tests",
        headers=_auth(),
    )
    assert ready_for_tests.status_code == 200, ready_for_tests.text
    assert ready_for_tests.json()["status"] == "ready_for_tests"

    failed_tests = client.post(
        f"/v1/agents/{agent_id}/change-sets/{cs_body['id']}/ready-for-review",
        headers=_auth(),
        json={
            "eval_results_ref": "eval/run/refund-core/red",
            "required_eval_suites": ["refund-core"],
            "passed": False,
        },
    )
    assert failed_tests.status_code == 400, failed_tests.text

    ready_for_review = client.post(
        f"/v1/agents/{agent_id}/change-sets/{cs_body['id']}/ready-for-review",
        headers=_auth(),
        json={
            "eval_results_ref": "eval/run/refund-core/green",
            "required_eval_suites": ["refund-core"],
            "passed": True,
        },
    )
    assert ready_for_review.status_code == 200, ready_for_review.text
    assert ready_for_review.json()["status"] == "ready_for_review"

    rc = client.post(
        f"/v1/agents/{agent_id}/change-sets/{cs_body['id']}/release-candidates",
        headers=_auth(),
        json={"required_eval_suites": ["refund-core"], "required_approvals": ["owner"]},
    )
    assert rc.status_code == 201, rc.text
    rc_body = rc.json()
    assert rc_body["status"] == "ready_for_approval"
    assert rc_body["change_set_id"] == cs_body["id"]
    assert rc_body["candidate_version_id"]
    assert rc_body["readiness"][0]["status"] == "passed"

    blocked = client.post(
        f"/v1/agents/{agent_id}/release-candidates/{rc_body['id']}/gate",
        headers=_auth(),
        json={
            "gate_id": "eval:refund-core",
            "status": "failed",
            "evidence_ref": "eval/run/refund-core/regressed",
            "message": "Refund current-policy eval regressed.",
        },
    )
    assert blocked.status_code == 200, blocked.text
    assert blocked.json()["status"] == "blocked"

    blocked_approval = client.post(
        f"/v1/agents/{agent_id}/release-candidates/{rc_body['id']}/approve",
        headers=_auth(),
        json={"approval_id": "owner", "comment": "Reviewed."},
    )
    assert blocked_approval.status_code == 400, blocked_approval.text

    unblocked = client.post(
        f"/v1/agents/{agent_id}/release-candidates/{rc_body['id']}/gate",
        headers=_auth(),
        json={
            "gate_id": "eval:refund-core",
            "status": "passed",
            "evidence_ref": "eval/run/refund-core/green",
            "message": "Required eval suite passed.",
        },
    )
    assert unblocked.status_code == 200, unblocked.text
    assert unblocked.json()["status"] == "ready_for_approval"

    approved = client.post(
        f"/v1/agents/{agent_id}/release-candidates/{rc_body['id']}/approve",
        headers=_auth(),
        json={"approval_id": "owner", "comment": "Reviewed Change Package input."},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "deployable"

    workflow = client.get(f"/v1/agents/{agent_id}/workflow", headers=_auth())
    assert workflow.status_code == 200, workflow.text
    assert workflow.json()["branches"][0]["id"] == branch_body["id"]
    assert workflow.json()["change_sets"][0]["status"] == "converted_to_release_candidate"
    assert workflow.json()["release_candidates"][0]["id"] == rc_body["id"]

    versions = client.get(f"/v1/agents/{agent_id}/versions", headers=_auth())
    assert versions.status_code == 200, versions.text
    version_spec = versions.json()["items"][0]["spec"]
    assert version_spec["branch_id"] == branch_body["id"]
    assert version_spec["change_set_id"] == cs_body["id"]

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert {event["action"] for event in audit} >= {
        "agent_workflow:branch_create",
        "agent_workflow:change_set_create",
        "agent_workflow:change_set_ready_for_tests",
        "agent_workflow:change_set_ready_for_review",
        "agent_workflow:release_candidate_create",
        "agent_workflow:release_candidate_gate",
        "agent_workflow:release_candidate_approve",
    }


def test_change_package_preflight_links_commitment_evidence_and_stales_on_change(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    release_candidate = _create_deployable_release_candidate(
        client,
        agent_id,
        name="Refund policy preflight",
    )
    package = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "release_candidate_id": release_candidate["id"],
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
    assert body["change_set_id"] == release_candidate["change_set_id"]
    assert body["release_candidate_id"] == release_candidate["id"]
    assert body["commitment_document_id"].startswith("commit_")
    assert body["evidence"]["commitment"] == body["commitment_document_id"]
    assert body["evidence"]["change_set"] == release_candidate["change_set_id"]
    assert body["evidence"]["release_candidate"] == release_candidate["id"]
    assert body["required_approvals"][0]["role"] == "Agent owner"

    submitted = client.post(
        f"/v1/agents/{agent_id}/change-packages/{body['id']}/submit",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "submitted"
    assert submitted.json()["submitted_at"] is not None
    notifications = submitted.json()["approval_notifications"]
    assert {item["approval_id"] for item in notifications} == {"owner", "compliance"}
    assert all(item["content_hash"] == body["content_hash"] for item in notifications)
    assert all(
        f"/agents/{agent_id}/deploys?change_package_id={body['id']}"
        in item["deep_link"]
        for item in notifications
    )
    stored_notifications = client.app.state.cp.ux_wireup[  # type: ignore[attr-defined]
        "change_package_approval_notifications"
    ][body["id"]]
    assert stored_notifications == notifications

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


def test_change_package_preflight_requires_approved_release_candidate_when_named(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    missing = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "release_candidate_id": "rc_missing",
            "summary": "Attempt preflight for an unknown release candidate.",
        },
    )
    assert missing.status_code == 404, missing.text
    assert "unknown release candidate" in missing.json()["message"]

    branch = client.post(
        f"/v1/agents/{agent_id}/branches",
        headers=_auth(),
        json={"name": "blocked-rc", "base_version_id": "v1"},
    )
    assert branch.status_code == 201, branch.text
    change_set = client.post(
        f"/v1/agents/{agent_id}/change-sets",
        headers=_auth(),
        json={
            "branch_id": branch.json()["id"],
            "name": "Blocked release candidate",
            "summary": "Create a release candidate that has not been approved.",
            "changed_objects": [{"type": "behavior", "id": "behavior.refund"}],
        },
    )
    assert change_set.status_code == 201, change_set.text
    ready_for_tests = client.post(
        f"/v1/agents/{agent_id}/change-sets/{change_set.json()['id']}/ready-for-tests",
        headers=_auth(),
    )
    assert ready_for_tests.status_code == 200, ready_for_tests.text
    ready_for_review = client.post(
        f"/v1/agents/{agent_id}/change-sets/{change_set.json()['id']}/ready-for-review",
        headers=_auth(),
        json={
            "eval_results_ref": "eval/run/refund-core/green",
            "required_eval_suites": ["refund-core"],
            "passed": True,
        },
    )
    assert ready_for_review.status_code == 200, ready_for_review.text
    rc = client.post(
        f"/v1/agents/{agent_id}/change-sets/{change_set.json()['id']}/release-candidates",
        headers=_auth(),
        json={"required_eval_suites": ["refund-core"], "required_approvals": ["owner"]},
    )
    assert rc.status_code == 201, rc.text
    assert rc.json()["status"] == "ready_for_approval"

    blocked = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "release_candidate_id": rc.json()["id"],
            "summary": "Attempt preflight before release candidate approval.",
        },
    )
    assert blocked.status_code == 400, blocked.text
    assert "must be approved or deployable" in blocked.json()["message"]


def test_change_package_requested_approvals_can_expire(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    package = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "from_version_id": "v1",
            "to_version_id": "v2",
            "target_environment": "production",
            "summary": "Promote refund policy update.",
            "risk_summary": "Production refund policy changed.",
        },
    )
    assert package.status_code == 201, package.text

    submitted = client.post(
        f"/v1/agents/{agent_id}/change-packages/{package.json()['id']}/submit",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["approval_status"] == "blocked"

    expired = client.post(
        f"/v1/agents/{agent_id}/change-packages/{package.json()['id']}/approvals/expire",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "approval_ids": ["compliance"],
            "reason": "Compliance review SLA elapsed.",
        },
    )
    assert expired.status_code == 200, expired.text
    body = expired.json()
    assert body["status"] == "changes_requested"
    assert body["approval_status"] == "expired"
    compliance = next(
        item for item in body["required_approvals"] if item["id"] == "compliance"
    )
    assert compliance["state"] == "expired"
    assert compliance["satisfied"] is False
    assert compliance["expired_reason"] == "Compliance review SLA elapsed."
    owner = next(item for item in body["required_approvals"] if item["id"] == "owner")
    assert owner["state"] == "requested"

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert "change_package:approval_expire" in {event["action"] for event in audit}


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

    activity = client.post(
        f"/v1/agents/{agent_id}/channel-bindings/{body['id']}/activity",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "status": "failure",
            "trace_id": "trace_whatsapp_template_failure",
            "occurred_at": "2026-05-10T10:00:00Z",
            "failure_message": "Template language was rejected by provider.",
        },
    )
    assert activity.status_code == 200, activity.text
    assert activity.json()["last_traffic_at"].startswith("2026-05-10T10:00:00")
    assert activity.json()["last_failure_at"].startswith("2026-05-10T10:00:00")

    relisted = client.get(
        f"/v1/agents/{agent_id}/channel-bindings",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert relisted.status_code == 200, relisted.text
    relisted_whatsapp = next(
        item for item in relisted.json()["items"] if item["channel_type"] == "whatsapp"
    )
    assert relisted_whatsapp["last_traffic_at"].startswith("2026-05-10T10:00:00")
    assert relisted_whatsapp["last_failure_at"].startswith("2026-05-10T10:00:00")

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert {event["action"] for event in audit} >= {
        "channel_binding:upsert",
        "channel_binding:readiness",
        "channel_binding:activity",
    }


def test_channel_preview_matrix_and_formatting_eval_case(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    for channel_type, provider in [
        ("whatsapp", "Meta Cloud API"),
        ("sms", "Twilio SMS"),
        ("email", "Loop Mail Router"),
    ]:
        created = client.post(
            f"/v1/agents/{agent_id}/channel-bindings",
            headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
            json={
                "channel_type": channel_type,
                "provider": provider,
                "display_name": f"Acme {channel_type}",
                "identity_config": {"owner": "support"},
                "auth_config_ref": f"secret://channels/{channel_type}/acme",
            },
        )
        assert created.status_code == 201, created.text

    matrix = client.post(
        f"/v1/agents/{agent_id}/channel-bindings/preview-matrix",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "scenario_title": "Duplicate charge",
            "user_message": "I was charged twice for my renewal.",
            "expected_outcome": (
                "Acknowledge the duplicate charge, verify the account, explain the "
                "refund path, mention the SLA, explain escalation, and include "
                "opt-out language for short-message channels."
            ),
            "channel_types": ["whatsapp", "sms", "email"],
        },
    )
    assert matrix.status_code == 200, matrix.text
    body = matrix.json()
    assert body["summary"]["channels"] == 3
    rows = {row["channel_type"]: row for row in body["rows"]}
    assert rows["whatsapp"]["rendered_preview"].startswith("Acknowledge")
    assert rows["email"]["rendered_preview"].startswith("Subject: Duplicate charge")
    sms_length_failure = next(
        failure for failure in rows["sms"]["formatting_failures"] if failure["id"] == "sms_too_long"
    )

    seed = rows["sms"]["eval_case_seed"]
    saved = client.post(
        f"/v1/agents/{agent_id}/channel-bindings/preview-matrix/eval-cases",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={**seed, "failure_reason": sms_length_failure["message"]},
    )
    assert saved.status_code == 201, saved.text
    assert saved.json()["case"]["source"] == "channel-preview-matrix"
    assert saved.json()["case"]["input"]["channel_type"] == "sms"

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert "channel_binding:preview_eval_case" in {event["action"] for event in audit}


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
    _mark_channel_ready(client, workspace_id, agent_id, "web_chat")
    _mark_channel_ready(client, workspace_id, agent_id, "whatsapp")
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
    assert deployment["stage"] == "canary"
    assert deployment["status"] == "canary"
    assert deployment["trafficPercent"] == 10
    assert deployment["evidencePackId"] == evidence_pack["id"]
    assert evidence_pack["change_package_id"] == package["id"]
    assert evidence_pack["version_manifest"]["content_hash"] == package["content_hash"]
    assert (
        evidence_pack["version_manifest"]["release_candidate_id"] == package["release_candidate_id"]
    )

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

    export = client.post(
        f"/v1/agents/{agent_id}/evidence-packs/{evidence_pack['id']}/exports",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"format": "json", "purpose": "security review", "redactions": ["pricing"]},
    )
    assert export.status_code == 201, export.text
    exported = export.json()
    assert exported["status"] == "ready"
    assert exported["format"] == "json"
    assert exported["evidence_pack_id"] == evidence_pack["id"]
    assert exported["change_package_id"] == package["id"]
    assert "change_package" in exported["sections"]
    assert "eval_results" in exported["sections"]
    assert "audit_log" in exported["sections"]
    assert any(ref.startswith("change-package/") for ref in exported["artifact_refs"])
    assert {"secrets", "raw_tool_credentials", "pricing"} <= set(exported["redactions"])
    assert exported["download_url"].endswith(exported["id"])

    download = client.get(
        exported["download_url"],
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert download.status_code == 200, download.text
    downloaded = download.json()
    assert downloaded["id"] == exported["id"]
    assert downloaded["evidence_pack"]["id"] == evidence_pack["id"]
    assert downloaded["format"] == "json"
    assert downloaded["purpose"] == "security review"
    assert downloaded["change_package_id"] == package["id"]
    assert "pricing" in downloaded["redactions"]
    assert "audit_log" in downloaded["sections"]
    assert "raw secrets" in downloaded["secret_policy"].lower()

    fabricated = client.get(
        f"/v1/agents/{agent_id}/evidence-packs/{evidence_pack['id']}/exports/epex_fabricated",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert fabricated.status_code == 404, fabricated.text

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert {event["action"] for event in audit} >= {
        "deployment:start",
        "deployment:promote",
        "evidence_pack:export",
        "evidence_pack:export_download",
    }


def test_approved_change_package_can_start_shadow_rollout(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    _mark_channel_ready(client, workspace_id, agent_id, "web_chat")
    package = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "from_version_id": "v1",
            "to_version_id": "v2",
            "summary": "Shadow the approved draft before canary traffic.",
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
            "stage": "shadow",
            "traffic_percent": 50,
            "channel_scope": ["web_chat"],
            "region_scope": ["us-east-1"],
        },
    )
    assert started.status_code == 201, started.text
    deployment = started.json()["deployment"]
    evidence_pack = started.json()["evidence_pack"]
    assert deployment["stage"] == "shadow"
    assert deployment["status"] == "shadow"
    assert deployment["trafficPercent"] == 0
    assert evidence_pack["canary_results_ref"].endswith("/shadow")


def test_deployment_start_blocks_only_channels_with_incomplete_readiness(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    _mark_channel_ready(client, workspace_id, agent_id, "web_chat")
    package = client.post(
        f"/v1/agents/{agent_id}/change-packages/preflight",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "from_version_id": "v1",
            "to_version_id": "v2",
            "summary": "Promote only the channels that are ready.",
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

    web_only = client.post(
        f"/v1/agents/{agent_id}/deployments/start",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "change_package_id": package["id"],
            "version_id": "v2",
            "traffic_percent": 5,
            "channel_scope": ["web_chat"],
        },
    )
    assert web_only.status_code == 201, web_only.text
    assert web_only.json()["deployment"]["channelScope"] == ["web_chat"]

    blocked = client.post(
        f"/v1/agents/{agent_id}/deployments/start",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "change_package_id": package["id"],
            "version_id": "v2",
            "traffic_percent": 5,
            "channel_scope": ["whatsapp"],
        },
    )
    assert blocked.status_code == 400, blocked.text
    assert "channel readiness blocks rollout: whatsapp not_configured" in blocked.json()["message"]

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    blocked_events = [event for event in audit if event["action"] == "deployment:start_blocked"]
    assert blocked_events
    payload = client.app.state.cp.audit_events.fetch_payload(  # type: ignore[attr-defined]
        blocked_events[0]["payload_hash"]
    )
    assert payload["channel_blockers"][0]["channel_type"] == "whatsapp"


def test_deployment_threshold_evaluation_records_no_action_when_healthy(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    deployment = _start_canary_deployment(
        client,
        workspace_id,
        agent_id,
        thresholds={"error_rate": 0.02},
    )

    evaluated = client.post(
        f"/v1/agents/{agent_id}/deployments/{deployment['id']}/thresholds/evaluate",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"metric": "error_rate", "observed": 0.01, "policy": "rollback"},
    )

    assert evaluated.status_code == 200, evaluated.text
    body = evaluated.json()
    assert body["decision"] == "no_action"
    assert body["breached"] is False
    assert body["threshold"] == 0.02
    assert body["deployment"]["status"] == "canary"

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    threshold_events = [
        event for event in audit if event["action"] == "deployment:threshold_evaluate"
    ]
    assert threshold_events
    payload = client.app.state.cp.audit_events.fetch_payload(  # type: ignore[attr-defined]
        threshold_events[0]["payload_hash"]
    )
    assert payload["decision"] == "no_action"
    assert payload["breached"] is False


def test_deployment_threshold_breach_pauses_rollout_by_policy(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    deployment = _start_canary_deployment(
        client,
        workspace_id,
        agent_id,
        thresholds={"tool_failure_rate": 0.03},
    )
    trace_id = "8" * 32
    _add_trace(client, workspace_id, agent_id, trace_id)

    evaluated = client.post(
        f"/v1/agents/{agent_id}/deployments/{deployment['id']}/thresholds/evaluate",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "metric": "tool_failure_rate",
            "observed": 0.08,
            "policy": "pause",
            "window": "10m",
        },
    )

    assert evaluated.status_code == 200, evaluated.text
    body = evaluated.json()
    assert body["decision"] == "paused"
    assert body["breached"] is True
    assert body["deployment"]["status"] == "paused"
    assert body["deployment"]["stage"] == "paused"
    assert body["incident"]["status"] == "contained"
    assert body["incident"]["deployment_id"] == deployment["id"]
    assert body["incident"]["affected_trace_ids"] == [trace_id]
    assert body["incident"]["report"]["rollback_status"] == "paused"
    assert body["incident"]["report"]["affected_channels"] == ["web_chat"]
    assert body["incident"]["report"]["actions_taken"] == [
        f"deployment/{deployment['id']}/pause"
    ]

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert {event["action"] for event in audit} >= {
        "deployment:threshold_breach",
        "deployment:pause",
        "incident:create_auto_pause",
    }


def test_deployment_threshold_breach_rolls_back_and_creates_incident(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    deployment = _start_canary_deployment(
        client,
        workspace_id,
        agent_id,
        thresholds={"error_rate": 0.02},
    )
    trace_id = "6" * 32
    _add_trace(client, workspace_id, agent_id, trace_id)

    evaluated = client.post(
        f"/v1/agents/{agent_id}/deployments/{deployment['id']}/thresholds/evaluate",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "metric": "error_rate",
            "observed": 0.04,
            "policy": "rollback",
            "window": "5m",
            "reason": "Provider outage pushed the canary above the error budget.",
        },
    )

    assert evaluated.status_code == 200, evaluated.text
    body = evaluated.json()
    assert body["decision"] == "rolled_back"
    assert body["breached"] is True
    assert body["deployment"]["status"] == "rolled_back"
    assert body["deployment"]["trafficPercent"] == 0
    assert body["incident"]["deployment_id"] == deployment["id"]
    assert body["incident"]["report"]["rollback_status"] == "executed"

    listed = client.get(
        f"/v1/agents/{agent_id}/incidents",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert listed.status_code == 200, listed.text
    incident = listed.json()["items"][0]
    assert incident["status"] == "contained"
    assert incident["deployment_id"] == deployment["id"]
    assert incident["trigger"] == "error_rate breached 0.04 > 0.02 over 5m"
    assert incident["affected_trace_ids"] == [trace_id]
    assert incident["report"]["affected_channels"] == ["web_chat"]
    assert incident["report"]["timeline"]

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert {event["action"] for event in audit} >= {
        "deployment:threshold_breach",
        "deployment:rollback",
        "incident:create_auto_rollback",
    }


def test_canary_rollout_can_ramp_before_production_promotion(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    deployment = _start_canary_deployment(client, workspace_id, agent_id)

    ramped = client.post(
        f"/v1/agents/{agent_id}/deployments/{deployment['id']}/ramp",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"traffic_percent": 50},
    )
    assert ramped.status_code == 200, ramped.text
    assert ramped.json()["stage"] == "ramp"
    assert ramped.json()["status"] == "ramp"
    assert ramped.json()["trafficPercent"] == 50

    promoted = client.post(
        f"/v1/agents/{agent_id}/deployments/{deployment['id']}/promote",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["status"] == "live"
    assert promoted.json()["stage"] == "production"
    assert promoted.json()["trafficPercent"] == 100

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert "deployment:ramp" in {event["action"] for event in audit}


def test_live_rollout_cannot_ramp_after_production_promotion(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    live = _start_live_deployment(client, workspace_id, agent_id)

    ramped = client.post(
        f"/v1/agents/{agent_id}/deployments/{live['id']}/ramp",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"traffic_percent": 50},
    )
    assert ramped.status_code == 400, ramped.text
    assert "cannot ramp from live" in ramped.json()["message"]


def test_observed_failure_eval_case_closes_90_second_editing_loop(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    response = client.post(
        f"/v1/agents/{agent_id}/eval-cases/from-observed-failure",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "sentence_id": "sentence_purpose_cancel",
            "sentence_text": "When a customer asks to cancel, cite May 2026 policy.",
            "sentence_role": "promise",
            "trace_id": "trace_refund_742",
            "failure_reason": ("Agent cited archived policy before current May 2026 policy."),
            "expected_outcome": ("Cite the May 2026 refund policy before quoting refund window."),
            "proposed_fix": (
                "Add a behavior rule requiring current policy citation before refund windows."
            ),
            "replay_ref": "replay/run/trace_refund_742/fixed",
            "channel": "web_chat",
            "version_ref": "version/v23",
            "risk_tags": ["risk_eval_gap"],
            "target_object_kind": "knowledge_chunk",
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
    assert body["case"]["input"]["target_object_kind"] == "knowledge_chunk"
    assert body["case"]["input"]["channel"] == "web_chat"
    assert body["case"]["input"]["version_ref"] == "version/v23"
    assert body["case"]["input"]["risk_tags"] == ["risk_eval_gap"]
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


def test_behavior_repair_proposal_runs_replay_summary_before_eval_save(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    response = client.post(
        f"/v1/agents/{agent_id}/behavior/repair-proposals",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "sentence_id": "sentence_purpose_cancel",
            "sentence_text": "When a customer asks to cancel, cite May 2026 policy.",
            "sentence_role": "promise",
            "trace_id": "trace_refund_742",
            "failure_reason": "Agent cited archived policy before current policy.",
            "replay_ref": "replay/run/trace_refund_742/fixed",
            "risk_tags": ["risk_eval_gap"],
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"].startswith("repair_")
    assert body["target_object"]["kind"] == "knowledge_chunk"
    assert body["target_object"]["label"] == "Responsible knowledge source"
    assert body["proposal"]["evidence_ref"] == "trace_refund_742"
    assert body["replay"]["draft_ref"] == "replay/run/trace_refund_742/fixed"
    assert body["replay"]["regressed"] == 0
    assert "save_regression_eval" in body["next_actions"]

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert "behavior:repair_proposal:create" in {event["action"] for event in audit}


def test_incident_response_links_auto_rollback_and_seeds_eval_cases(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    live = _start_live_deployment(client, workspace_id, agent_id)
    trace_id = "5" * 32
    _add_trace(client, workspace_id, agent_id, trace_id)

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
    assert incident["affected_trace_ids"] == [trace_id]
    assert incident["affected_conversation_count"] == 1
    assert incident["report"]["suspected_cause"].startswith("Tool schema")
    assert incident["report"]["candidate_regression_tests"] == [trace_id]
    assert incident["report"]["rollback_status"] == "executed"
    assert incident["report"]["timeline"]
    assert incident["report"]["affected_trace_ids"] == [trace_id]
    assert incident["report"]["affected_channels"] == ["web_chat"]
    assert incident["report"]["actions_taken"] == [f"deployment/{live['id']}/rollback"]
    assert [item["recipient"] for item in incident["notifications"]] == ["owner-1"]
    assert incident["report"]["notifications"][0]["summary"].startswith("high incident")
    assert "affected_traces_collected" in {event["kind"] for event in incident["timeline"]}

    seeded = client.post(
        f"/v1/agents/{agent_id}/incidents/{incident['id']}/eval-cases",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert seeded.status_code == 201, seeded.text
    assert seeded.json()["ok"] is True
    assert seeded.json()["suite_id"]
    assert seeded.json()["case_ids"]
    assert seeded.json()["incident"]["candidate_eval_suite_id"] == seeded.json()["suite_id"]
    assert len(seeded.json()["case_ids"]) == 1

    fix_package = client.post(
        f"/v1/agents/{agent_id}/incidents/{incident['id']}/change-package",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert fix_package.status_code == 201, fix_package.text
    fix_body = fix_package.json()
    assert fix_body["ok"] is True
    assert fix_body["change_package"]["summary"].startswith("Fix incident")
    assert fix_body["change_package"]["eval_results_ref"] == seeded.json()["suite_id"]
    assert fix_body["change_package"]["semantic_diff"][0]["dimension"] == "incident"
    assert fix_body["incident"]["status"] == "fix_staged"
    assert fix_body["incident"]["fix_change_package_id"] == fix_body["change_package"]["id"]
    assert fix_body["incident"]["report"]["fix_change_package_id"]
    assert "fix_change_package_created" in {
        event["kind"] for event in fix_body["incident"]["timeline"]
    }

    investigating = client.post(
        f"/v1/agents/{agent_id}/incidents/{incident['id']}/investigate",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"note": "Root cause owner is checking the provider schema change."},
    )
    assert investigating.status_code == 200, investigating.text
    assert investigating.json()["status"] == "investigating"

    resolved = client.post(
        f"/v1/agents/{agent_id}/incidents/{incident['id']}/resolve",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"note": "Fix package staged and regression evals are green."},
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["resolved_at"] is not None

    archived = client.post(
        f"/v1/agents/{agent_id}/incidents/{incident['id']}/archive",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"note": "Postmortem evidence exported."},
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"

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
        "incident:fix_change_package_created",
        "incident:investigating",
        "incident:resolved",
        "incident:archived",
        "change_package:generate_from_incident",
    }
    rollback_incident_audit = next(
        event for event in audit if event["action"] == "incident:create_auto_rollback"
    )
    payload = client.app.state.cp.audit_events.fetch_payload(  # type: ignore[attr-defined]
        rollback_incident_audit["payload_hash"]
    )
    assert payload["affected_trace_count"] == 1
    assert payload["notification_targets"] == ["owner-1"]


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


def test_workspace_comment_threads_are_listed_for_review(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    thread = {
        "id": "th_live_refund",
        "agentId": str(agent_id),
        "anchor": {
            "objectId": "trace-prod-1",
            "kind": "transcript_turn",
            "authoredAt": "v23",
        },
        "observedAt": "v23",
        "comments": [
            {
                "id": "cmt_live_refund",
                "threadId": "th_live_refund",
                "authorId": "reviewer-1",
                "authorDisplay": "Reviewer",
                "body": "The agent should refund premium customers directly.",
                "createdAt": "2026-05-09T00:00:00Z",
                "anchor": {
                    "objectId": "trace-prod-1",
                    "kind": "transcript_turn",
                    "authoredAt": "v23",
                },
                "evidenceRef": "audit/comments/cmt_live_refund",
            }
        ],
    }
    ux_wireup = client.app.state.cp.ux_wireup  # type: ignore[attr-defined]
    ux_wireup.setdefault("comment_threads", {}).setdefault(str(workspace_id), []).append(
        thread
    )

    response = client.get(
        f"/v1/workspaces/{workspace_id}/comment-threads",
        headers=_auth(),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["items"][0]["id"] == "th_live_refund"
    assert body["items"][0]["agentId"] == str(agent_id)
    assert body["items"][0]["comments"][0]["id"] == "cmt_live_refund"


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
    initial_security = client.get(
        f"/v1/workspaces/{workspace_id}/enterprise/security",
        headers=_auth(),
    )
    assert initial_security.status_code == 200, initial_security.text
    assert initial_security.json()["byok_keys"][0]["status"] == "missing"

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

    rotated_security = client.get(
        f"/v1/workspaces/{workspace_id}/enterprise/security",
        headers=_auth(),
    ).json()
    assert rotated_security["byok_keys"][0]["status"] == "rotated"
    assert rotated_security["residency_zones"][0]["active"] is True

    revoke = client.post(
        f"/v1/workspaces/{workspace_id}/encryption/key/revoke",
        headers=_auth(),
    ).json()
    assert revoke["workspace_disabled"] is True
    assert revoke["status"] == "revoked"

    revoked_security = client.get(
        f"/v1/workspaces/{workspace_id}/enterprise/security",
        headers=_auth(),
    ).json()
    assert revoked_security["byok_keys"][0]["status"] == "missing"

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

    retrieval_eval = client.post(
        f"/v1/agents/{agent_id}/kb/retrieval-eval-cases",
        headers=_auth(),
        json={
            "query": "How do refunds work after final sale?",
            "top_chunk_id": "chunk_refunds",
            "candidate_chunk_ids": ["chunk_refunds", "chunk_legal"],
            "metadata_filters": ["locale:any", "workspace:acme"],
            "expected_citation": "refund_policy.pdf#p3",
            "evidence_ref": "retrieval.final_sale_refund.requires_exception",
            "missed_candidate_ids": ["chunk_exception"],
        },
    )
    assert retrieval_eval.status_code == 201, retrieval_eval.text
    assert retrieval_eval.json()["case"]["source"] == "knowledge-retrieval"
    assert (
        retrieval_eval.json()["case"]["expected"]["citation"]
        == "refund_policy.pdf#p3"
    )

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
    assert tool.json()["tool_contract"]["sandbox_status"] == "sandbox"
    assert tool.json()["tool_contract"]["side_effect_level"] == "write"
    assert tool.json()["tool_contract"]["live_status"] == "review_required"

    refund_tool = client.post(
        f"/v1/agents/{agent_id}/tools/import",
        headers=_auth(),
        json={
            "source": "curl -X POST https://api.example.test/refunds",
            "source_kind": "curl",
        },
    )
    assert refund_tool.status_code == 200, refund_tool.text
    assert refund_tool.json()["tool_contract"]["money_movement"] is True
    assert refund_tool.json()["tool_contract"]["budget_limits"] == {}
    assert refund_tool.json()["tool_contract"]["live_status"] == "blocked"

    contracts = client.get(f"/v1/agents/{agent_id}/tool-contracts", headers=_auth())
    assert contracts.status_code == 200, contracts.text
    imported_tool_ids = {item["tool_id"] for item in contracts.json()["items"]}
    assert tool.json()["tool_id"] in imported_tool_ids
    assert refund_tool.json()["tool_id"] in imported_tool_ids

    persona = client.post(
        f"/v1/agents/{agent_id}/persona-test",
        headers=_auth(),
        json={"persona_set": "first-user"},
    )
    assert len(persona.json()["items"]) == 5
    persona_item = persona.json()["items"][0]
    persona_eval = client.post(
        f"/v1/agents/{agent_id}/persona-test/eval-cases",
        headers=_auth(),
        json={
            "persona_set": "first-user",
            "persona": persona_item["persona"],
            "candidate_eval_id": persona_item["candidate_eval_id"],
            "evidence_ref": persona_item["evidence_ref"],
            "scenarios": persona_item["scenarios"],
            "failed_scenarios": persona_item["failed_scenarios"],
            "pass_rate": persona_item["pass_rate"],
            "expected_behavior": "Preserve grounded answers for this persona cluster.",
            "risk_tags": ["persona-test", persona_item["persona"]],
        },
    )
    assert persona_eval.status_code == 201, persona_eval.text
    assert persona_eval.json()["case"]["source"] == "persona-test"
    assert persona_eval.json()["case"]["source_ref"] == persona_item["evidence_ref"]

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
    share_body = share.json()
    assert share_body["url"].startswith("/share/")
    viewed_by_id = client.get(f"/v1/shares/{share_body['id']}", headers=_auth())
    assert viewed_by_id.json()["redaction_banner"].startswith("2 redaction")
    viewed_by_token = client.get(
        f"/v1/shares/{share_body['url'].rsplit('/', 1)[-1]}",
        headers=_auth(),
    )
    assert viewed_by_token.json()["source_id"] == "2" * 32


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
    assert clips[0]["url"] == "/help/clips/canary-slider"
    assert clips[0]["frames"]

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
    demo_body = demo.json()
    assert demo_body["url"].startswith("/voice-demo/")
    assert demo_body["mic_test_required"] is True
    token = demo_body["url"].rsplit("/", 1)[-1]

    public_demo = client.get(f"/v1/voice-demo/{token}")
    assert public_demo.status_code == 200, public_demo.text
    assert public_demo.json()["snapshot_id"] == "snap_123"
    assert public_demo.json()["duration_cap_minutes"] == 5

    session = client.post(f"/v1/voice-demo/{token}/sessions")
    assert session.status_code == 201, session.text
    assert session.json()["room"].startswith("voice-demo-")

    audit_actions = {
        event["action"]
        for event in client.get(
            f"/v1/audit-events?workspace_id={workspace_id}",
            headers=_auth(),
        ).json()["items"]
    }
    assert "voice_demo:view" in audit_actions
    assert "voice_demo:session_start" in audit_actions

    _add_trace(client, workspace_id, agent_id, "3" * 32)
    activity = client.get(f"/v1/workspaces/{workspace_id}/activity", headers=_auth())
    assert activity.json()["turn_rate_per_minute"] == 1
