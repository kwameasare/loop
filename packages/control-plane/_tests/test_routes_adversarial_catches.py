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


@pytest.fixture
def member_auth(client: TestClient, workspace_id: UUID) -> dict[str, str]:
    response = client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers=_auth(),
        json={"user_sub": "alice", "role": "member"},
    )
    assert response.status_code == 201, response.text
    return _auth("alice")


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
            "proposed_patch": (
                "Never approve refunds over $500 cumulatively within one conversation "
                "without manual review."
            ),
            "create_eval_cases": True,
        },
    )
    assert resolved.status_code == 200, resolved.text
    body = resolved.json()
    assert body["status"] == "resolved"
    assert (
        body["resolution"]["proposed_patch"]
        == "Never approve refunds over $500 cumulatively within one conversation without manual review."
    )
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


def test_adversarial_probe_budgets_are_workspace_configurable_by_risk_class(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
) -> None:
    default_budget = client.get(
        f"/v1/workspaces/{workspace_id}/adversarial-probe-budgets",
        headers=_auth(),
    )
    assert default_budget.status_code == 200, default_budget.text
    assert default_budget.json()["budgets"]["high"] == 4000

    updated = client.patch(
        f"/v1/workspaces/{workspace_id}/adversarial-probe-budgets",
        headers=_auth(),
        json={"high": 900, "medium": 1500},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["budgets"]["high"] == 900

    run = client.post(
        f"/v1/agents/{agent_id}/adversarial-probes/run",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "rule_id": "refund_cap",
            "rule_text": "Never approve refunds over $500.",
            "risk_class": "high",
        },
    )
    assert run.status_code == 201, run.text
    assert run.json()["run"]["budget_tokens"] == 900

    audit = client.get(f"/v1/audit-events?workspace_id={workspace_id}", headers=_auth())
    assert "adversarial_probe:budget_update" in {item["action"] for item in audit.json()["items"]}


def test_members_can_read_but_not_mutate_adversarial_catches(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
    member_auth: dict[str, str],
) -> None:
    run = client.post(
        f"/v1/agents/{agent_id}/adversarial-probes/run",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "rule_id": "refund_cap",
            "rule_text": "Never approve refunds over $500.",
            "risk_class": "high",
        },
    )
    assert run.status_code == 201, run.text
    catch = run.json()["catches"][0]

    budgets = client.get(
        f"/v1/workspaces/{workspace_id}/adversarial-probe-budgets",
        headers=member_auth,
    )
    assert budgets.status_code == 200, budgets.text

    listed = client.get(
        f"/v1/agents/{agent_id}/catches",
        headers={**member_auth, "x-loop-workspace-id": str(workspace_id)},
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["items"][0]["id"] == catch["id"]

    budget_update = client.patch(
        f"/v1/workspaces/{workspace_id}/adversarial-probe-budgets",
        headers=member_auth,
        json={"high": 900},
    )
    assert budget_update.status_code == 403, budget_update.text

    member_run = client.post(
        f"/v1/agents/{agent_id}/adversarial-probes/run",
        headers={**member_auth, "x-loop-workspace-id": str(workspace_id)},
        json={
            "rule_id": "member_probe",
            "rule_text": "Always answer in one sentence.",
            "risk_class": "low",
        },
    )
    assert member_run.status_code == 403, member_run.text

    resolved = client.post(
        f"/v1/agents/{agent_id}/catches/{catch['id']}/resolve",
        headers={**member_auth, "x-loop-workspace-id": str(workspace_id)},
        json={
            "intended_interpretation": "Apply cumulatively.",
            "rejected_interpretation": "Do not split the cap.",
            "create_eval_cases": True,
        },
    )
    assert resolved.status_code == 403, resolved.text
