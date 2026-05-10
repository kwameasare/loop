"""FastAPI routes for Studio Memory Studio wire-up."""

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


@pytest.fixture
def client(env: None) -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def workspace_id(client: TestClient) -> UUID:
    response = client.post(
        "/v1/workspaces",
        headers={"authorization": _bearer_for("owner-1")},
        json={"name": "Acme", "slug": "acme"},
    )
    return UUID(response.json()["id"])


@pytest.fixture
def agent_id(client: TestClient, workspace_id: UUID) -> UUID:
    response = client.post(
        "/v1/agents",
        headers={
            "authorization": _bearer_for("owner-1"),
            "x-loop-workspace-id": str(workspace_id),
        },
        json={"name": "Support Bot", "slug": "support-bot"},
    )
    return UUID(response.json()["id"])


@pytest.mark.asyncio
async def test_agent_memory_route_lists_and_deletes_user_memory(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    cp = client.app.state.cp  # type: ignore[attr-defined]
    await cp.user_memory_store.set_user(
        workspace_id=workspace_id,
        agent_id=agent_id,
        user_id="owner-1",
        key="preferred_language",
        value="English",
    )

    listed = client.get(
        f"/v1/agents/{agent_id}/memory?user_id=owner-1",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["items"][0]["key"] == "preferred_language"
    assert listed.json()["items"][0]["after"] == "English"
    assert listed.json()["items"][0]["source_trace"] == ""
    assert listed.json()["items"][0]["confidence"] == "low"
    assert "missing_source_trace" in listed.json()["items"][0]["safety_flags"]

    deleted = client.delete(
        f"/v1/agents/{agent_id}/memory/user/preferred_language?user_id=owner-1",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert deleted.status_code == 204, deleted.text

    after = client.get(
        f"/v1/agents/{agent_id}/memory?user_id=owner-1",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert after.json()["items"] == []


@pytest.mark.asyncio
async def test_agent_memory_route_surfaces_source_trace_evidence(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    cp = client.app.state.cp  # type: ignore[attr-defined]
    source_turn_id = UUID("11111111-1111-4111-8111-111111111111")
    await cp.user_memory_store.set_user(
        workspace_id=workspace_id,
        agent_id=agent_id,
        user_id="owner-1",
        key="preferred_language",
        value="English",
        source_trace="trace_refund_2026_05_10",
        source_turn_id=source_turn_id,
        source_span_id="span_memory_write",
        write_reason='User said "English is fine".',
        policy_ref="memory_policy/user:v1",
    )

    response = client.get(
        f"/v1/agents/{agent_id}/memory?user_id=owner-1",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code == 200, response.text
    item = response.json()["items"][0]
    assert item["source"] == 'User said "English is fine".'
    assert item["source_trace"] == "trace_refund_2026_05_10"
    assert item["source_turn_id"] == str(source_turn_id)
    assert item["source_span_id"] == "span_memory_write"
    assert item["policy_ref"] == "memory_policy/user:v1"
    assert item["confidence"] == "medium"
    assert item["safety_flags"] == ["none"]
    assert "memory_policy/user:v1" in item["retention_policy"]


@pytest.mark.asyncio
async def test_agent_memory_route_redacts_secret_like_values(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    cp = client.app.state.cp  # type: ignore[attr-defined]
    await cp.user_memory_store.set_user(
        workspace_id=workspace_id,
        agent_id=agent_id,
        user_id="owner-1",
        key="payment_hint",
        value={"card": "4111-1111-1111-1111"},
    )

    response = client.get(
        f"/v1/agents/{agent_id}/memory?user_id=owner-1",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["after"] == "[redacted secret-like value]"


@pytest.mark.asyncio
async def test_agent_memory_cross_user_access_requires_admin(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    added = client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers={"authorization": _bearer_for("owner-1")},
        json={"user_sub": "alice", "role": "member"},
    )
    assert added.status_code == 201, added.text

    cp = client.app.state.cp  # type: ignore[attr-defined]
    await cp.user_memory_store.set_user(
        workspace_id=workspace_id,
        agent_id=agent_id,
        user_id="owner-1",
        key="preferred_language",
        value="English",
    )
    await cp.user_memory_store.set_user(
        workspace_id=workspace_id,
        agent_id=agent_id,
        user_id="alice",
        key="preferred_channel",
        value="WhatsApp",
    )

    self_read = client.get(
        f"/v1/agents/{agent_id}/memory?user_id=alice",
        headers={"authorization": _bearer_for("alice")},
    )
    assert self_read.status_code == 200, self_read.text
    assert self_read.json()["items"][0]["key"] == "preferred_channel"

    cross_read = client.get(
        f"/v1/agents/{agent_id}/memory?user_id=owner-1",
        headers={"authorization": _bearer_for("alice")},
    )
    assert cross_read.status_code == 403

    cross_delete = client.delete(
        f"/v1/agents/{agent_id}/memory/user/preferred_language?user_id=owner-1",
        headers={"authorization": _bearer_for("alice")},
    )
    assert cross_delete.status_code == 403

    admin_delete = client.delete(
        f"/v1/agents/{agent_id}/memory/user/preferred_channel?user_id=alice",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert admin_delete.status_code == 204, admin_delete.text


def test_agent_session_memory_lookup_requires_admin(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    added = client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers={"authorization": _bearer_for("owner-1")},
        json={"user_sub": "alice", "role": "member"},
    )
    assert added.status_code == 201, added.text

    denied = client.get(
        f"/v1/agents/{agent_id}/memory?conversation_id=11111111-1111-4111-8111-111111111111",
        headers={"authorization": _bearer_for("alice")},
    )
    assert denied.status_code == 403

    allowed = client.get(
        f"/v1/agents/{agent_id}/memory?conversation_id=11111111-1111-4111-8111-111111111111",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert allowed.status_code == 200, allowed.text


def test_agent_memory_route_requires_membership(client: TestClient, agent_id: UUID) -> None:
    response = client.get(
        f"/v1/agents/{agent_id}/memory?user_id=owner-1",
        headers={"authorization": _bearer_for("stranger")},
    )
    assert response.status_code in (401, 403)


def test_agent_memory_policies_support_enterprise_scopes(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    headers = {
        "authorization": _bearer_for("owner-1"),
        "x-loop-workspace-id": str(workspace_id),
    }
    base_body = {
        "allowed_memory_types": ["trace_backed_fact"],
        "retention": "Retain for 90 days unless superseded.",
        "consent_requirement": "Admin consent required before activation.",
        "pii_policy": "No secrets, payment data, or individual PII.",
        "delete_behavior": "Delete on request with audit trail.",
        "privacy_implications": ["This memory can affect future agent behavior."],
        "source_trace_required": True,
    }

    for scope in ["account", "organization", "task", "agent"]:
        scope_body = {
            **base_body,
            "scope": scope,
            "pii_policy": "No sensitive values." if scope == "task" else base_body["pii_policy"],
        }
        response = client.put(
            f"/v1/agents/{agent_id}/memory-policies/{scope}",
            headers=headers,
            json=scope_body,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["scope"] == scope
        assert body["source_trace_required"] is True
        assert body["content_hash"]
        if scope == "task":
            assert body["approval_status"] == "draft"
        else:
            assert body["approval_status"] == "review_required"

    approved = client.post(
        f"/v1/agents/{agent_id}/memory-policies/account/approve",
        headers=headers,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["approval_status"] == "approved"

    listed = client.get(
        f"/v1/agents/{agent_id}/memory-policies",
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    scopes = {item["scope"] for item in listed.json()["items"]}
    assert {"account", "organization", "task", "agent"} <= scopes

    audit = client.get(f"/v1/audit-events?workspace_id={workspace_id}", headers=headers)
    actions = {item["action"] for item in audit.json()["items"]}
    assert {"memory_policy:upsert", "memory_policy:approve"} <= actions
