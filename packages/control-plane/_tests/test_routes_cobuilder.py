"""Tests for the AI Co-Builder workspace route."""

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


def test_cobuilder_derives_actions_from_latest_agent_version(
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
                "system_prompt": "Answer refunds with evidence.",
                "tools": ["lookup_order", "issue_refund"],
                "memory_rules": ["preferred_language"],
            }
        },
    )

    response = client.get(
        f"/v1/workspaces/{workspace_id}/cobuilder",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["agentId"] == str(agent_id)
    assert body["operator"]["maxMode"] == "drive"
    assert "tools:write" in body["operator"]["scopes"]
    assert any(
        action["id"] == "act_gate_side_effect_tool" for action in body["actions"]
    )
    assert body["rubberDuck"]["proposedFix"]["id"] == body["review"]["actionId"]
    assert len(body["review"]["bullets"]) == 5


def test_cobuilder_downgrades_viewer_consent(
    client: TestClient,
) -> None:
    workspace_id = _workspace(client)
    client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers={"authorization": _bearer_for("owner-1")},
        json={"user_sub": "viewer-1", "role": "viewer"},
    )

    response = client.get(
        f"/v1/workspaces/{workspace_id}/cobuilder",
        headers={"authorization": _bearer_for("viewer-1")},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["operator"]["maxMode"] == "suggest"
    assert body["operator"]["scopes"] == ["agent:read"]
    assert body["actions"][0]["id"] == "act_create_first_agent"


def test_cobuilder_apply_creates_branch_changeset_and_audit(
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
                "system_prompt": "Answer refunds with evidence.",
                "tools": ["lookup_order", "issue_refund"],
            }
        },
    )

    response = client.post(
        f"/v1/workspaces/{workspace_id}/cobuilder/actions/act_gate_side_effect_tool/apply",
        headers=headers,
        json={
            "agent_id": str(agent_id),
            "selection_context": f"agents/{agent_id}/tools/issue_refund.yaml",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["evidenceRef"].endswith("/act_gate_side_effect_tool/applied")
    assert body["branch"]["name"] == "cobuilder/act-gate-side-effect-tool"
    assert body["changeSet"]["source_type"] == "ai_cobuilder"
    changed = body["changeSet"]["changed_objects"][0]
    assert changed["action_id"] == "act_gate_side_effect_tool"
    assert changed["mode"] == "edit"
    assert changed["selection_context"].endswith("/tools/issue_refund.yaml")
    assert body["nextUrl"].endswith(f"/deploys?change_set={body['changeSet']['id']}")

    workflow = client.get(
        f"/v1/agents/{agent_id}/workflow",
        headers=headers,
    )
    assert workflow.status_code == 200, workflow.text
    workflow_body = workflow.json()
    assert any(item["id"] == body["branch"]["id"] for item in workflow_body["branches"])
    assert any(
        item["id"] == body["changeSet"]["id"]
        for item in workflow_body["change_sets"]
    )

    audit = client.get(f"/v1/audit-events?workspace_id={workspace_id}", headers=headers)
    assert audit.status_code == 200, audit.text
    assert "cobuilder:action_apply" in {item["action"] for item in audit.json()["items"]}


def test_cobuilder_apply_requires_admin_even_when_member_has_edit_consent(
    client: TestClient,
) -> None:
    workspace_id = _workspace(client)
    agent_id = _agent(client, workspace_id)
    owner_headers = {"authorization": _bearer_for("owner-1")}
    client.post(
        f"/v1/agents/{agent_id}/versions",
        headers=owner_headers,
        json={
            "spec": {
                "system_prompt": "Answer refunds with evidence.",
                "tools": ["issue_refund"],
            }
        },
    )
    client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers=owner_headers,
        json={"user_sub": "member-1", "role": "member"},
    )
    member_headers = {"authorization": _bearer_for("member-1")}

    workspace = client.get(
        f"/v1/workspaces/{workspace_id}/cobuilder",
        headers=member_headers,
    )
    assert workspace.status_code == 200, workspace.text
    assert workspace.json()["operator"]["maxMode"] == "edit"
    assert any(
        action["id"] == "act_replay_before_promote"
        for action in workspace.json()["actions"]
    )

    response = client.post(
        f"/v1/workspaces/{workspace_id}/cobuilder/actions/act_replay_before_promote/apply",
        headers=member_headers,
        json={"agent_id": str(agent_id)},
    )

    assert response.status_code == 403, response.text
