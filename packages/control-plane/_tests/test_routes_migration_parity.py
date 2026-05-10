"""Tests for the migration parity workspace route."""

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


def test_migration_parity_derives_readiness_from_agent_version_and_traces(
    client: TestClient,
) -> None:
    workspace_id = _workspace(client)
    agent_id = _agent(client, workspace_id)
    headers = {"authorization": _bearer_for("owner-1")}
    client.post(
        f"/v1/agents/{agent_id}/versions",
        headers=headers,
        json={
            "spec": {
                "system_prompt": "Preserve imported refund behavior.",
                "tools": ["lookup_order", "issue_refund"],
                "migration": {
                    "archive": "acme.bpz",
                    "archive_sha": "sha256:" + ("a" * 64),
                },
            }
        },
    )
    cp = client.app.state.cp  # type: ignore[attr-defined]
    cp.trace_store.add(
        TraceSummary(
            workspace_id=workspace_id,
            trace_id="b" * 32,
            turn_id=uuid4(),
            conversation_id=uuid4(),
            agent_id=agent_id,
            started_at=datetime(2026, 5, 4, 11, 0, tzinfo=UTC),
            duration_ms=100,
            span_count=3,
        )
    )

    response = client.get(
        f"/v1/workspaces/{workspace_id}/migration/parity",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["lineage"]["archive"] == "acme.bpz"
    assert body["readiness"]["parityPassing"] == 1
    assert any(diff["id"] == "diff_risk_tools" for diff in body["diffs"])
    assert any(repair["id"] == "rep_tool_safety_contract" for repair in body["repairs"])
    assert body["cutover"]["rollbackTriggers"][0]["metric"] == "regression"


def test_migration_parity_requires_workspace_membership(
    client: TestClient,
) -> None:
    workspace_id = _workspace(client)

    response = client.get(
        f"/v1/workspaces/{workspace_id}/migration/parity",
        headers={"authorization": _bearer_for("stranger")},
    )

    assert response.status_code in (401, 403)


def test_botpress_import_creates_durable_lineage_and_cutover_state(
    client: TestClient,
) -> None:
    workspace_id = _workspace(client)
    headers = {"authorization": _bearer_for("owner-1")}

    created = client.post(
        f"/v1/workspaces/{workspace_id}/migrations/imports",
        headers=headers,
        json={
            "source": "botpress",
            "archive_name": "acme-refunds.bpz",
            "archive_sha": "sha256:" + ("c" * 64),
            "target_agent_name": "Acme Imported Concierge",
            "business_responsibility": "Preserve refund support behavior.",
            "channels": ["web_chat", "whatsapp"],
            "inventory": {"integrations": 0, "unsupported_nodes": 0},
            "transcript_count": 20,
        },
    )

    assert created.status_code == 201, created.text
    run = created.json()
    assert run["source"] == "botpress"
    assert run["target_agent_id"]
    assert run["target_branch_id"].startswith("br_")
    assert run["target_change_set_id"].startswith("cs_")
    assert run["commitment_document_id"].startswith("commit_")
    assert run["readiness"]["parity_total"] == 20
    assert run["cutover_stages"][0]["status"] == "in_progress"
    assert {ref["source_ref"] for ref in run["eval_case_refs"]} >= {
        f"migration/{run['id']}/import/smoke",
        f"migration/{run['id']}/import/transcripts",
    }
    generated_suite_id = run["eval_case_refs"][0]["suite_id"]
    generated_cases = client.get(
        f"/v1/eval-suites/{generated_suite_id}/cases",
        headers=headers,
    )
    assert generated_cases.status_code == 200, generated_cases.text
    generated_sources = {case["source"] for case in generated_cases.json()["items"]}
    assert {"migration_import", "migration_transcript"} <= generated_sources

    agents = client.get(
        "/v1/agents",
        headers={**headers, "x-loop-workspace-id": str(workspace_id)},
    ).json()["items"]
    assert any(agent["id"] == run["target_agent_id"] for agent in agents)

    workflow = client.get(
        f"/v1/agents/{run['target_agent_id']}/workflow",
        headers=headers,
    ).json()
    assert workflow["branches"][0]["id"] == run["target_branch_id"]
    assert workflow["change_sets"][0]["id"] == run["target_change_set_id"]

    parity = client.get(
        f"/v1/workspaces/{workspace_id}/migration/parity",
        headers=headers,
        params={"migration_id": run["id"]},
    )
    assert parity.status_code == 200, parity.text
    parity_body = parity.json()
    assert parity_body["migrationRun"]["id"] == run["id"]
    assert parity_body["lineage"]["archive"] == "acme-refunds.bpz"
    assert parity_body["lineage"]["steps"][3]["id"] == "branch"
    assert any(diff["sourcePath"] == "botpress.intents" for diff in parity_body["diffs"])

    advanced = client.post(
        f"/v1/workspaces/{workspace_id}/migrations/imports/{run['id']}/cutover/advance",
        headers=headers,
        json={"stage_id": "canary_1pct", "evidence_ref": "audit/canary/green"},
    )

    assert advanced.status_code == 200, advanced.text
    advanced_body = advanced.json()
    assert advanced_body["status"] == "cutover_active"
    assert advanced_body["cutover_stages"][0]["status"] == "passed"
    assert advanced_body["cutover_stages"][1]["status"] == "in_progress"

    rolled_back = client.post(
        f"/v1/workspaces/{workspace_id}/migrations/imports/{run['id']}/cutover/rollback",
        headers=headers,
        json={"trigger_id": "manual", "reason": "operator test"},
    )

    assert rolled_back.status_code == 200, rolled_back.text
    assert rolled_back.json()["status"] == "rolled_back"
    actions = [
        event.action
        for event in client.app.state.cp.audit_events.list_for_workspace(workspace_id)  # type: ignore[attr-defined]
    ]
    assert "migration:import_create" in actions
    assert "migration:cutover_advance" in actions
    assert "migration:cutover_rollback" in actions
    import_event = next(
        event
        for event in client.app.state.cp.audit_events.list_for_workspace(workspace_id)  # type: ignore[attr-defined]
        if event.action == "migration:import_create"
    )
    import_payload = client.app.state.cp.audit_events.fetch_payload(  # type: ignore[attr-defined]
        import_event.payload_hash
    )
    assert import_payload["generated_eval_cases"] == len(run["eval_case_refs"])


def test_accepting_migration_repair_resolves_blocker_and_arms_cutover(
    client: TestClient,
) -> None:
    workspace_id = _workspace(client)
    headers = {"authorization": _bearer_for("owner-1")}

    created = client.post(
        f"/v1/workspaces/{workspace_id}/migrations/imports",
        headers=headers,
        json={
            "source": "botpress",
            "archive_name": "acme-refunds.bpz",
            "target_agent_name": "Acme Imported Concierge",
            "business_responsibility": "Preserve refund support behavior.",
            "channels": ["web_chat", "whatsapp"],
            "transcript_count": 20,
        },
    )
    assert created.status_code == 201, created.text
    run = created.json()
    assert run["status"] == "mapped"
    assert run["readiness"]["blocking_count"] >= 1
    assert run["cutover_stages"][0]["status"] == "pending"

    accepted = client.post(
        f"/v1/workspaces/{workspace_id}/migrations/imports/{run['id']}/repairs/rep_inv_integrations/accept",
        headers=headers,
        json={
            "evidence_ref": "audit/migration/accept/integrations",
            "patch_summary": "Attach sandbox tool contracts for imported integrations.",
        },
    )

    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["status"] == "parity_ready"
    assert body["readiness"]["blocking_count"] == 0
    assert body["cutover_stages"][0]["status"] == "in_progress"
    eval_ref = body["eval_case_refs"][0]
    assert eval_ref["repair_id"] == "rep_inv_integrations"
    assert eval_ref["source_ref"] == f"migration/{run['id']}/repair/rep_inv_integrations"
    inventory = {item["id"]: item for item in body["inventory"]}
    assert inventory["inv_integrations"]["severity"] == "ok"
    assert inventory["inv_integrations"]["resolved_by_repair_id"] == "rep_inv_integrations"

    cases = client.get(
        f"/v1/eval-suites/{eval_ref['suite_id']}/cases",
        headers=headers,
    )
    assert cases.status_code == 200, cases.text
    case = cases.json()["items"][0]
    assert case["id"] == eval_ref["case_id"]
    assert case["source"] == "migration_repair"
    assert case["input"]["repair_id"] == "rep_inv_integrations"
    assert case["input"]["agent_id"] == run["target_agent_id"]
    assert case["expected"]["cutover_blocking"] is False
    assert case["scorers"][0]["kind"] == "migration_parity"

    parity = client.get(
        f"/v1/workspaces/{workspace_id}/migration/parity",
        headers=headers,
        params={"migration_id": run["id"]},
    )
    assert parity.status_code == 200, parity.text
    assert not any(
        repair["id"] == "rep_inv_integrations" for repair in parity.json()["repairs"]
    )
    actions = [
        event.action
        for event in client.app.state.cp.audit_events.list_for_workspace(workspace_id)  # type: ignore[attr-defined]
    ]
    assert "migration:repair_accept" in actions
    repair_event = next(
        event
        for event in client.app.state.cp.audit_events.list_for_workspace(workspace_id)  # type: ignore[attr-defined]
        if event.action == "migration:repair_accept"
    )
    audit_payload = client.app.state.cp.audit_events.fetch_payload(  # type: ignore[attr-defined]
        repair_event.payload_hash
    )
    assert audit_payload["eval_case"]["case_id"] == eval_ref["case_id"]


def test_migration_import_supports_dialogflow_cx_source_profile(
    client: TestClient,
) -> None:
    workspace_id = _workspace(client)
    headers = {"authorization": _bearer_for("owner-1")}

    created = client.post(
        f"/v1/workspaces/{workspace_id}/migrations/imports",
        headers=headers,
        json={
            "source": "dialogflow_cx",
            "archive_name": "billing-agent-cx.zip",
            "target_agent_name": "Billing CX Migration",
            "business_responsibility": "Preserve billing support outcomes.",
            "channels": ["web_chat", "email"],
            "inventory": {"webhooks": 0, "fulfillment": 0},
            "transcript_count": 15,
        },
    )

    assert created.status_code == 201, created.text
    run = created.json()
    assert run["source"] == "dialogflow_cx"
    assert run["source_profile"]["label"] == "Dialogflow CX export"
    assert "CX agent export zip" in run["source_profile"]["accepted_inputs"]
    inventory = {item["kind"]: item for item in run["inventory"]}
    assert inventory["pages"]["loop_target"] == "behavior policies + page routes"
    assert inventory["entities"]["loop_target"] == "slot/entity extraction"
    assert inventory["channels"]["count"] == 2
    assert run["lineage_steps"][0]["detail"].startswith("Parsed `billing-agent-cx.zip`")
