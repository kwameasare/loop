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


def test_adversarial_probe_creates_calm_catch_and_resolution_eval_cases(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
) -> None:
    run = client.post(
        f"/v1/agents/{agent_id}/adversarial-probes/run",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "rule_id": "refund_cap",
            "rule_text": "Never approve refunds over $500.",
            "risk_class": "high",
            "budget_tokens": 2000,
        },
    )
    assert run.status_code == 201, run.text
    catch = run.json()["catches"][0]
    assert catch["status"] == "open"
    assert "per refund call or cumulatively" in catch["question"]
    assert catch["evidence_ref"].startswith("adversarial_probe/")

    resolved = client.post(
        f"/v1/agents/{agent_id}/catches/{catch['id']}/resolve",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "intended_interpretation": "Apply the cap cumulatively per conversation.",
            "rejected_interpretation": "Do not split a refund into multiple calls to bypass cap.",
            "create_eval_cases": True,
        },
    )
    assert resolved.status_code == 200, resolved.text
    body = resolved.json()
    assert body["status"] == "resolved"
    assert len(body["eval_case_refs"]) == 2

    listed = client.get(
        f"/v1/agents/{agent_id}/catches",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["items"][0]["status"] == "resolved"

    audit = client.get(f"/v1/audit-events?workspace_id={workspace_id}", headers=_auth())
    assert {
        "adversarial_probe:run",
        "adversarial_catch:resolve",
    } <= {item["action"] for item in audit.json()["items"]}


def test_adversarial_catch_can_be_dismissed_without_eval_cases(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
) -> None:
    run = client.post(
        f"/v1/agents/{agent_id}/adversarial-probes/run",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "rule_id": "tone_rule",
            "rule_text": "Always be concise.",
            "risk_class": "low",
        },
    )
    catch = run.json()["catches"][0]
    dismissed = client.post(
        f"/v1/agents/{agent_id}/catches/{catch['id']}/resolve",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "dismiss_reason": "Already covered by channel-specific tests.",
            "create_eval_cases": True,
        },
    )
    assert dismissed.status_code == 200, dismissed.text
    assert dismissed.json()["status"] == "dismissed"
    assert dismissed.json()["eval_case_refs"] == []
