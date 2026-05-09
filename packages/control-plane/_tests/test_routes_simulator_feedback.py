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
        json={"name": "Support Bot", "slug": "support-bot"},
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def test_simulator_turn_rating_creates_eval_case_and_audit_event(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
) -> None:
    response = client.post(
        f"/v1/agents/{agent_id}/simulator/turn-ratings",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "rating": "bad",
            "prompt": "Can I get a refund after the deadline?",
            "final_answer": "Yes, always.",
            "channel": "whatsapp",
            "trace_id": "trace_first_proof_1",
            "issue_annotation": "Should cite policy and escalate exceptions.",
            "save_as_eval": True,
            "cost_usd": 0.012,
            "latency_ms": 840,
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["rating"] == "bad"
    assert body["candidate_artifact"]["kind"] == "regression_eval_candidate"
    assert body["eval_case_ref"]["case"]["source"] == "first-proof:bad"
    assert (
        body["eval_case_ref"]["case"]["expected"]["outcome"]
        == "Should cite policy and escalate exceptions."
    )

    listed = client.get(
        f"/v1/agents/{agent_id}/simulator/turn-ratings",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["items"][0]["id"] == body["id"]

    audit = client.get(f"/v1/audit-events?workspace_id={workspace_id}", headers=_auth())
    assert "simulator_turn:rate" in {item["action"] for item in audit.json()["items"]}


def test_simulator_turn_rating_can_capture_unclear_turn_without_eval(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
) -> None:
    response = client.post(
        f"/v1/agents/{agent_id}/simulator/turn-ratings",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "rating": "unclear",
            "prompt": "What happens now?",
            "final_answer": "It depends.",
            "channel": "web",
            "trace_id": "",
            "issue_annotation": "Ask a clarifying question before acting.",
            "save_as_eval": False,
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["candidate_artifact"]["kind"] == "clarification_note_candidate"
    assert body["eval_case_ref"] is None
