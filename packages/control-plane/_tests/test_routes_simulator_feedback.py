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
    assert body["behavior_note_ref"] is None
    assert body["few_shot_ref"] is None
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


def test_simulator_run_is_durable_and_audited(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
) -> None:
    response = client.post(
        f"/v1/agents/{agent_id}/simulator/runs",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "prompt": "Can I cancel my annual plan?",
            "final_answer": "I will check the renewal policy first.",
            "channel": "whatsapp",
            "trace_id": "trace_first_proof_run",
            "config": {
                "model_alias": "fast-draft",
                "memory_mode": "snapshot",
                "tool_mode": "mock",
            },
            "status": "completed",
            "cost_usd": 0.043,
            "latency_ms": 1030,
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"].startswith("simrun_")
    assert body["channel"] == "whatsapp"
    assert len(body["trace_id"]) == 32
    assert body["config"]["model_alias"] == "fast-draft"

    listed = client.get(
        f"/v1/agents/{agent_id}/simulator/runs",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["items"][0]["id"] == body["id"]

    trace = client.get(f"/v1/traces/{body['trace_id']}", headers=_auth())
    assert trace.status_code == 200, trace.text
    assert trace.json()["agent_id"] == str(agent_id)
    assert trace.json()["duration_ms"] == 1030

    audit = client.get(f"/v1/audit-events?workspace_id={workspace_id}", headers=_auth())
    assert "simulator_run:create" in {item["action"] for item in audit.json()["items"]}


def test_good_simulator_turn_rating_creates_few_shot_candidate(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
) -> None:
    response = client.post(
        f"/v1/agents/{agent_id}/simulator/turn-ratings",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "rating": "good",
            "prompt": "Can I cancel my annual plan?",
            "final_answer": "I can help. I will check the renewal policy first.",
            "channel": "telegram",
            "trace_id": "trace_first_proof_good",
            "simulator_run_id": "simrun_good",
            "issue_annotation": "Preserve the calm policy-check pattern.",
            "save_as_eval": False,
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["candidate_artifact"]["kind"] == "positive_eval_or_few_shot"
    assert body["simulator_run_id"] == "simrun_good"
    assert body["candidate_artifact"]["simulator_run_id"] == "simrun_good"
    assert body["few_shot_ref"]["status"] == "candidate"
    assert body["few_shot_ref"]["prompt"] == "Can I cancel my annual plan?"
    assert body["few_shot_ref"]["answer"].startswith("I can help.")
    assert body["few_shot_ref"]["channel"] == "telegram"
    assert body["few_shot_ref"]["evidence_ref"] == "trace_first_proof_good"
    assert body["behavior_note_ref"] is None
    assert body["eval_case_ref"] is None


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
    assert body["behavior_note_ref"]["kind"] == "clarification_prompt"
    assert body["behavior_note_ref"]["status"] == "candidate"
    assert body["behavior_note_ref"]["evidence_ref"].startswith("simulator-turn/")
    assert body["few_shot_ref"] is None
    assert body["eval_case_ref"] is None
