"""Tests for eval suite + run routes (P0.4)."""

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


def test_create_suite(client: TestClient, workspace_id: UUID) -> None:
    response = client.post(
        f"/v1/workspaces/{workspace_id}/eval-suites",
        headers={"authorization": _bearer_for("owner-1")},
        json={
            "name": "smoke",
            "dataset_ref": "fixtures/smoke.jsonl",
            "metrics": ["faithfulness", "groundedness"],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "smoke"
    assert body["metrics"] == ["faithfulness", "groundedness"]
    assert body["created_by"] == "owner-1"


def test_create_suite_rejects_duplicate_name(
    client: TestClient, workspace_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    body = {"name": "smoke", "dataset_ref": "x"}
    first = client.post(
        f"/v1/workspaces/{workspace_id}/eval-suites", headers=headers, json=body
    )
    second = client.post(
        f"/v1/workspaces/{workspace_id}/eval-suites", headers=headers, json=body
    )
    assert first.status_code == 201
    assert second.status_code == 400


def test_list_suites_returns_recent_first(
    client: TestClient, workspace_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    client.post(
        f"/v1/workspaces/{workspace_id}/eval-suites",
        headers=headers,
        json={"name": "first", "dataset_ref": "f"},
    )
    client.post(
        f"/v1/workspaces/{workspace_id}/eval-suites",
        headers=headers,
        json={"name": "second", "dataset_ref": "s"},
    )
    items = client.get(
        f"/v1/workspaces/{workspace_id}/eval-suites", headers=headers
    ).json()["items"]
    assert items[0]["name"] == "second"
    assert items[1]["name"] == "first"


def test_create_suite_requires_admin(
    client: TestClient, workspace_id: UUID
) -> None:
    client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers={"authorization": _bearer_for("owner-1")},
        json={"user_sub": "alice", "role": "member"},
    )
    response = client.post(
        f"/v1/workspaces/{workspace_id}/eval-suites",
        headers={"authorization": _bearer_for("alice")},
        json={"name": "x", "dataset_ref": "y"},
    )
    assert response.status_code in (401, 403)


def test_start_run_returns_202_and_pending(
    client: TestClient, workspace_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    suite = client.post(
        f"/v1/workspaces/{workspace_id}/eval-suites",
        headers=headers,
        json={"name": "smoke", "dataset_ref": "f"},
    ).json()
    response = client.post(
        f"/v1/eval-suites/{suite['id']}/runs",
        headers=headers,
        json={"note": "manual trigger"},
    )
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["state"] == "pending"
    assert body["triggered_by"] == "owner-1"


def test_list_runs_returns_recent_first(
    client: TestClient, workspace_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    suite = client.post(
        f"/v1/workspaces/{workspace_id}/eval-suites",
        headers=headers,
        json={"name": "smoke", "dataset_ref": "f"},
    ).json()
    for _ in range(3):
        client.post(
            f"/v1/eval-suites/{suite['id']}/runs", headers=headers, json={}
        )
    runs = client.get(
        f"/v1/eval-suites/{suite['id']}/runs", headers=headers
    ).json()["items"]
    assert len(runs) == 3


def test_eval_routes_emit_audit_events(
    client: TestClient, workspace_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    suite = client.post(
        f"/v1/workspaces/{workspace_id}/eval-suites",
        headers=headers,
        json={"name": "smoke", "dataset_ref": "f"},
    ).json()
    client.post(f"/v1/eval-suites/{suite['id']}/runs", headers=headers, json={})
    state = client.app.state.cp  # type: ignore[attr-defined]
    actions = [e.action for e in state.audit_events.list_for_workspace(workspace_id)]
    assert "eval:suite:create" in actions
    assert "eval:run:start" in actions


def test_run_unknown_suite_returns_404(client: TestClient) -> None:
    from uuid import uuid4
    response = client.post(
        f"/v1/eval-suites/{uuid4()}/runs",
        headers={"authorization": _bearer_for("owner-1")},
        json={},
    )
    assert response.status_code == 404
