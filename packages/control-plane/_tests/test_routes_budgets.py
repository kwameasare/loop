"""Tests for workspace budget routes (P0.4)."""

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


def test_get_budget_returns_unbounded_default(
    client: TestClient, workspace_id: UUID
) -> None:
    response = client.get(
        f"/v1/workspaces/{workspace_id}/budgets",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["daily_limit_usd"] is None
    assert body["hard_limit_usd"] is None
    assert body["spent_today_usd"] == "0"


def test_patch_budget_sets_limits(
    client: TestClient, workspace_id: UUID
) -> None:
    response = client.patch(
        f"/v1/workspaces/{workspace_id}/budgets",
        headers={"authorization": _bearer_for("owner-1")},
        json={"daily_limit_usd": "10.00", "hard_limit_usd": "100.00"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["daily_limit_usd"] == "10.00"
    assert body["hard_limit_usd"] == "100.00"


def test_patch_budget_partial_update(
    client: TestClient, workspace_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    client.patch(
        f"/v1/workspaces/{workspace_id}/budgets",
        headers=headers,
        json={"daily_limit_usd": "5.00", "hard_limit_usd": "50.00"},
    )
    # Update only daily_limit; hard_limit must persist.
    response = client.patch(
        f"/v1/workspaces/{workspace_id}/budgets",
        headers=headers,
        json={"daily_limit_usd": "7.50"},
    )
    body = response.json()
    assert body["daily_limit_usd"] == "7.50"
    assert body["hard_limit_usd"] == "50.00"


def test_patch_rejects_daily_above_hard(
    client: TestClient, workspace_id: UUID
) -> None:
    response = client.patch(
        f"/v1/workspaces/{workspace_id}/budgets",
        headers={"authorization": _bearer_for("owner-1")},
        json={"daily_limit_usd": "100.00", "hard_limit_usd": "50.00"},
    )
    assert response.status_code == 400


def test_patch_rejects_negative(
    client: TestClient, workspace_id: UUID
) -> None:
    response = client.patch(
        f"/v1/workspaces/{workspace_id}/budgets",
        headers={"authorization": _bearer_for("owner-1")},
        json={"daily_limit_usd": "-1.00"},
    )
    assert response.status_code == 422


def test_patch_requires_admin(
    client: TestClient, workspace_id: UUID
) -> None:
    client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers={"authorization": _bearer_for("owner-1")},
        json={"user_sub": "alice", "role": "member"},
    )
    response = client.patch(
        f"/v1/workspaces/{workspace_id}/budgets",
        headers={"authorization": _bearer_for("alice")},
        json={"daily_limit_usd": "1000.00"},
    )
    assert response.status_code in (401, 403)


def test_patch_emits_audit_event(
    client: TestClient, workspace_id: UUID
) -> None:
    client.patch(
        f"/v1/workspaces/{workspace_id}/budgets",
        headers={"authorization": _bearer_for("owner-1")},
        json={"daily_limit_usd": "10.00"},
    )
    state = client.app.state.cp  # type: ignore[attr-defined]
    actions = [e.action for e in state.audit_events.list_for_workspace(workspace_id)]
    assert "workspace:budget:update" in actions


def test_get_requires_membership(client: TestClient, workspace_id: UUID) -> None:
    response = client.get(
        f"/v1/workspaces/{workspace_id}/budgets",
        headers={"authorization": _bearer_for("stranger")},
    )
    assert response.status_code in (401, 403)
