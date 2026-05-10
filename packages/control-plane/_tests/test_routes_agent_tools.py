"""FastAPI route for Studio Tools Room wire-up."""

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
    return UUID(
        client.post(
            "/v1/workspaces",
            headers={"authorization": _bearer_for("owner-1")},
            json={"name": "Acme", "slug": "acme"},
        ).json()["id"]
    )


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


def test_agent_tools_route_reads_latest_version_spec(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    client.post(
        f"/v1/agents/{agent_id}/versions",
        headers=headers,
        json={
            "spec": {
                "tools": [
                    {
                        "id": "lookup_order",
                        "name": "lookup_order",
                        "kind": "http",
                        "description": "Look up order state.",
                        "source": "https://orders.example.test",
                    },
                    "kb.search",
                ]
            }
        },
    )

    response = client.get(f"/v1/agents/{agent_id}/tools", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["items"] == [
        {
            "id": "lookup_order",
            "name": "lookup_order",
            "kind": "http",
            "description": "Look up order state.",
            "source": "https://orders.example.test",
        },
        {
            "id": "kb.search",
            "name": "kb.search",
            "kind": "mcp",
            "description": "",
            "source": "agent-version-spec",
        },
    ]


def test_agent_tools_route_requires_workspace_membership(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    response = client.get(
        f"/v1/agents/{agent_id}/tools",
        headers={"authorization": _bearer_for("stranger")},
    )
    assert response.status_code in (401, 403)


def test_tool_call_telemetry_drives_contract_metrics(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    contract = client.put(
        f"/v1/agents/{agent_id}/tool-contracts/lookup_order",
        headers=headers,
        json={
            "name": "lookup_order",
            "description": "Look up order state.",
            "side_effect_level": "read",
            "pii_access": True,
            "money_movement": False,
            "rate_limits": {"per_minute": 300},
            "budget_limits": {},
            "sandbox_status": "sandbox",
            "owner_user_id": "owner-1",
            "approval_policy_id": "policy-read",
            "failure_behavior": "Answer with uncertainty.",
            "compensation_behavior": "No compensation required.",
        },
    )
    assert contract.status_code == 200, contract.text

    empty = client.get(
        f"/v1/agents/{agent_id}/tool-contracts/metrics",
        headers=headers,
    )
    assert empty.status_code == 200, empty.text
    assert empty.json()["items"][0]["measurement_status"] == "waiting_for_calls"
    assert empty.json()["items"][0]["production_usage_7d"] == 0

    first = client.post(
        f"/v1/agents/{agent_id}/tools/lookup_order/calls",
        headers=headers,
        json={
            "trace_id": "trace-order-1",
            "latency_ms": 140,
            "status": "success",
            "retry_count": 1,
            "pii_sent": 2,
            "schema_hash": "schema-v1",
        },
    )
    assert first.status_code == 200, first.text
    second = client.post(
        f"/v1/agents/{agent_id}/tools/lookup_order/calls",
        headers=headers,
        json={
            "trace_id": "trace-order-2",
            "latency_ms": 520,
            "status": "error",
            "retry_count": 0,
            "pii_sent": 1,
            "schema_hash": "schema-v1",
        },
    )
    assert second.status_code == 200, second.text

    measured = client.get(
        f"/v1/agents/{agent_id}/tool-contracts/metrics",
        headers=headers,
    )
    assert measured.status_code == 200, measured.text
    item = measured.json()["items"][0]
    assert item["measurement_status"] == "measured"
    assert item["production_usage_7d"] == 2
    assert item["success_rate_percent"] == 50.0
    assert item["p95_latency_ms"] == 520
    assert item["retry_rate_percent"] == 50.0
    assert item["failed_calls_7d"] == 1
    assert item["pii_sent_7d"] == 3
    assert item["evidence_ref"] == "tool-telemetry/lookup_order/2-calls"

    actions = [
        event.action
        for event in client.app.state.cp.audit_events.list_for_workspace(workspace_id)  # type: ignore[attr-defined]
    ]
    assert "tool_call:record" in actions
