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


def _contract() -> dict[str, object]:
    return {
        "business_responsibility": "Resolve billing cancellations safely.",
        "target_users": "Enterprise customers and support operators.",
        "owner_user_id": "maya@acme.test",
        "backup_owner_user_id": "diego@acme.test",
        "worst_case_failure": "Promises a refund outside policy.",
        "channels": ["web", "whatsapp", "voice"],
        "systems_touched": ["billing api", "crm"],
        "regions": ["us-east-1", "eu-west-2"],
        "languages": ["en", "es"],
        "success_metric": "95% eval pass rate before canary.",
        "compliance_domain": "SOC2 support operations",
        "expected_volume": "20k turns per month",
        "launch_date": "2026-06-01",
        "budget_target": "$0.08 per resolved turn",
        "out_of_scope": "Legal advice and refunds above policy.",
        "escalation_policy": "Escalate policy conflicts to the support lead.",
    }


def test_agent_intake_creates_governed_draft_and_seed_objects(
    client: TestClient,
    workspace_id: UUID,
) -> None:
    response = client.post(
        f"/v1/workspaces/{workspace_id}/agent-intakes",
        headers=_auth(),
        json={
            "agent_name": "Billing Support Agent",
            "slug": "billing-support",
            "creation_path": "business_intent",
            "contract": _contract(),
            "capabilities": ["Answer cancellation questions", "Escalate refund disputes"],
            "artifacts": [
                {
                    "name": "refund_policy.pdf",
                    "kind": "pdf",
                    "text": "Always escalate refund disputes. Customer email maya@example.test.",
                },
                {
                    "name": "support_transcripts.csv",
                    "kind": "transcript",
                    "text": "Never refund outside policy. Always refund duplicate charges.",
                },
            ],
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    agent_id = body["agent"]["id"]
    assert body["state"] == "draft_ready"
    assert body["commitment"]["created_from"] == "agent_intake:business_intent"
    assert body["readiness"]["score"] >= 60
    assert len(body["jobs"]) == 9
    assert body["sensitive_data_findings"][0]["kind"] == "email_address"
    assert body["candidate_channels"] == [
        {
            "channel": "web",
            "status": "draft",
            "readiness": "Sandbox binding created; production identity checks still pending.",
        },
        {
            "channel": "whatsapp",
            "status": "draft",
            "readiness": "Sandbox binding created; production identity checks still pending.",
        },
        {
            "channel": "voice",
            "status": "draft",
            "readiness": "Sandbox binding created; production identity checks still pending.",
        },
    ]
    assert {tool["tool_id"] for tool in body["candidate_tools"]} == {
        "mock_billing_api",
        "mock_crm",
    }
    assert {source["name"] for source in body["candidate_knowledge_sources"]} == {
        "refund_policy.pdf",
        "support_transcripts.csv",
    }
    assert len(body["created_object_refs"]["channel_bindings"]) == 3
    assert len(body["created_object_refs"]["tool_contracts"]) == 2
    assert len(body["created_object_refs"]["knowledge_documents"]) == 2
    assert len(body["created_object_refs"]["eval_cases"]) == 3
    assert body["created_object_refs"]["version"] == "v1"
    assert body["created_object_refs"]["branch"]["name"] == "main/draft"
    assert "Initial behavior generated" in body["readiness"]["ready"]
    assert "Draft branch main/draft created" in body["readiness"]["ready"]

    versions = client.get(
        f"/v1/agents/{agent_id}/versions",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert versions.status_code == 200, versions.text
    version = versions.json()["items"][0]
    assert version["spec"]["created_from"] == "agent_intake:business_intent"
    assert version["spec"]["commitment_document_id"] == body["commitment"]["id"]
    assert set(version["spec"]["channels"]) == {"web_chat", "whatsapp", "voice"}
    assert set(version["spec"]["tool_contracts"]) == {"mock_billing_api", "mock_crm"}
    assert len(version["spec"]["knowledge_documents"]) == 2
    assert version["spec"]["memory_policy_id"] == body["created_object_refs"]["memory_policy_id"]
    assert version["spec"]["eval_suite_id"] == body["created_object_refs"]["eval_suite_id"]

    workflow = client.get(
        f"/v1/agents/{agent_id}/workflow",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert workflow.status_code == 200, workflow.text
    assert workflow.json()["branches"][0]["name"] == "main/draft"
    assert workflow.json()["branches"][0]["base_version_id"] == "v1"

    registry = client.get(
        "/v1/agents",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert registry.status_code == 200, registry.text
    registry_agent = registry.json()["items"][0]
    assert registry_agent["owner_user_id"] == "maya@acme.test"
    assert registry_agent["backup_owner_user_id"] == "diego@acme.test"
    assert registry_agent["environment"] == "draft"
    assert registry_agent["health_status"] == "drafting"
    assert registry_agent["open_issue_count"] == 0
    assert registry_agent["open_issue_sources"] == []
    assert registry_agent["commitment_document_id"] == body["commitment"]["id"]
    assert registry_agent["commitment_status"] == "draft"

    channels = client.get(
        f"/v1/agents/{agent_id}/channel-bindings",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert channels.status_code == 200, channels.text
    configured = [
        item
        for item in channels.json()["items"]
        if item["channel_type"] in {"web_chat", "whatsapp", "voice"}
    ]
    assert {item["status"] for item in configured} == {"draft"}

    tools = client.get(
        f"/v1/agents/{agent_id}/tool-contracts",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert tools.status_code == 200, tools.text
    assert {item["sandbox_status"] for item in tools.json()["items"]} == {"mock"}

    memory = client.get(
        f"/v1/agents/{agent_id}/memory-policies",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert memory.status_code == 200, memory.text
    assert memory.json()["items"][0]["scope"] == "conversation"

    knowledge = client.get(
        f"/v1/agents/{agent_id}/kb/documents",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert knowledge.status_code == 200, knowledge.text
    assert {item["name"] for item in knowledge.json()["items"]} == {
        "refund_policy.pdf",
        "support_transcripts.csv",
    }

    listed = client.get(
        f"/v1/workspaces/{workspace_id}/agent-intakes",
        headers=_auth(),
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["items"][0]["id"] == body["id"]

    audit = client.get(f"/v1/audit-events?workspace_id={workspace_id}", headers=_auth())
    assert {"agent_intake:create", "agent_intake:draft_objects_create"} <= {
        item["action"] for item in audit.json()["items"]
    }


def test_agent_intake_requires_workspace_admin(
    client: TestClient,
    workspace_id: UUID,
) -> None:
    response = client.post(
        f"/v1/workspaces/{workspace_id}/agent-intakes",
        headers=_auth("stranger"),
        json={
            "agent_name": "Billing Support Agent",
            "slug": "billing-support",
            "creation_path": "business_intent",
            "contract": _contract(),
        },
    )

    assert response.status_code in (401, 403)


def test_agent_intake_infers_tool_contracts_from_api_artifacts(
    client: TestClient,
    workspace_id: UUID,
) -> None:
    contract = {**_contract(), "systems_touched": []}
    response = client.post(
        f"/v1/workspaces/{workspace_id}/agent-intakes",
        headers=_auth(),
        json={
            "agent_name": "Artifact Tool Agent",
            "slug": "artifact-tool-agent",
            "creation_path": "business_intent",
            "contract": contract,
            "artifacts": [
                {
                    "name": "refund-api.yaml",
                    "kind": "openapi",
                    "text": "openapi: 3.0.0\ninfo:\n  title: Refund API\npaths:\n  /refunds:\n    post: {}",
                    "source_ref": "upload/refund-api.yaml",
                },
                {
                    "name": "orders-curl.txt",
                    "kind": "curl",
                    "text": "curl -X GET https://orders.example.test/v1/orders/123",
                    "source_ref": "",
                },
            ],
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    agent_id = body["agent"]["id"]
    assert {tool["tool_id"] for tool in body["candidate_tools"]} == {
        "mock_refund_api",
        "mock_orders_api",
    }
    assert {
        tool["source"] for tool in body["candidate_tools"]
    } == {"artifact:openapi", "artifact:curl"}
    assert body["candidate_knowledge_sources"] == []
    assert len(body["created_object_refs"]["tool_contracts"]) == 2
    assert body["created_object_refs"]["knowledge_documents"] == []

    tools = client.get(
        f"/v1/agents/{agent_id}/tool-contracts",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert tools.status_code == 200, tools.text
    tool_rows = tools.json()["items"]
    assert {item["tool_id"] for item in tool_rows} == {
        "mock_refund_api",
        "mock_orders_api",
    }
    assert all(item["sandbox_status"] == "mock" for item in tool_rows)
    assert any("upload/refund-api.yaml" in item["description"] for item in tool_rows)
    assert any("Import mode: curl" in item["failure_behavior"] for item in tool_rows)


def test_agent_intake_infers_channel_bindings_from_legacy_artifacts(
    client: TestClient,
    workspace_id: UUID,
) -> None:
    contract = {**_contract(), "channels": []}
    response = client.post(
        f"/v1/workspaces/{workspace_id}/agent-intakes",
        headers=_auth(),
        json={
            "agent_name": "Legacy Channel Agent",
            "slug": "legacy-channel-agent",
            "creation_path": "legacy_import",
            "contract": contract,
            "artifacts": [
                {
                    "name": "botpress-export.json",
                    "kind": "botpress_export",
                    "text": '{"channels": ["whatsapp", "telegram"], "handoff": "slack app"}',
                    "source_ref": "upload/botpress-export.json",
                },
            ],
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    agent_id = body["agent"]["id"]
    channel_candidates = body["candidate_channels"]
    assert {item["channel"] for item in channel_candidates} == {
        "whatsapp",
        "telegram",
        "slack",
    }
    assert {item["source"] for item in channel_candidates} == {
        "artifact:botpress_export"
    }
    assert len(body["created_object_refs"]["channel_bindings"]) == 3

    channels = client.get(
        f"/v1/agents/{agent_id}/channel-bindings",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert channels.status_code == 200, channels.text
    configured = {
        item["channel_type"]: item
        for item in channels.json()["items"]
        if item["channel_type"] in {"whatsapp", "telegram", "slack"}
    }
    assert set(configured) == {"whatsapp", "telegram", "slack"}
    assert {
        item["identity_config"]["source_artifact"] for item in configured.values()
    } == {"upload/botpress-export.json"}


def test_enterprise_template_intake_clones_approved_defaults(
    client: TestClient,
    workspace_id: UUID,
) -> None:
    templates = client.get(
        f"/v1/workspaces/{workspace_id}/agent-intake-templates",
        headers=_auth(),
    )
    assert templates.status_code == 200, templates.text
    support_template = next(
        item for item in templates.json()["items"] if item["id"] == "tmpl_support_agent"
    )
    assert support_template["summary"].startswith("Policy-grounded")
    assert support_template["contract"]["channels"] == ["web", "whatsapp", "email"]
    assert support_template["artifacts"][0]["source_ref"].startswith("template/tmpl_support_agent")

    response = client.post(
        f"/v1/workspaces/{workspace_id}/agent-intakes",
        headers=_auth(),
        json={
            "agent_name": "Template Support Agent",
            "slug": "template-support",
            "creation_path": "enterprise_template",
            "template_id": "tmpl_support_agent",
            "contract": {
                "owner_user_id": "maya@acme.test",
                "backup_owner_user_id": "diego@acme.test",
            },
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["creation_path"] == "enterprise_template"
    assert body["created_object_refs"]["template_id"] == "tmpl_support_agent"
    assert body["commitment"]["body"]["business_responsibility"].startswith(
        "Resolve support questions"
    )
    assert body["commitment"]["body"]["channels"] == ["web", "whatsapp", "email"]
    assert {tool["tool_id"] for tool in body["candidate_tools"]} == {
        "mock_crm",
        "mock_billing_api",
    }
    assert body["artifact_reports"][0]["source_ref"] == "template/tmpl_support_agent/runbook"
