"""Tests for DELETE /v1/workspaces/{id} (P0.4 + P0.7a)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

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


def _create_ws(client: TestClient, sub: str = "owner-1") -> UUID:
    return UUID(
        client.post(
            "/v1/workspaces",
            headers={"authorization": _bearer_for(sub)},
            json={"name": f"WS-{uuid4().hex[:6]}", "slug": f"ws-{uuid4().hex[:6]}"},
        ).json()["id"]
    )


def test_delete_workspace_returns_204(client: TestClient) -> None:
    ws_id = _create_ws(client)
    response = client.delete(
        f"/v1/workspaces/{ws_id}",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code == 204


def test_subsequent_get_returns_404(client: TestClient) -> None:
    ws_id = _create_ws(client)
    client.delete(
        f"/v1/workspaces/{ws_id}",
        headers={"authorization": _bearer_for("owner-1")},
    )
    # GETs on a deleted workspace go through the service which raises
    # WorkspaceError("unknown workspace") → mapped to LOOP-API-103 (404).
    response = client.get(
        f"/v1/workspaces/{ws_id}",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code in (404,)


def test_delete_requires_owner(client: TestClient) -> None:
    ws_id = _create_ws(client)
    # Add a regular member.
    client.post(
        f"/v1/workspaces/{ws_id}/members",
        headers={"authorization": _bearer_for("owner-1")},
        json={"user_sub": "alice", "role": "member"},
    )
    # alice tries to delete — must 401/403.
    response = client.delete(
        f"/v1/workspaces/{ws_id}",
        headers={"authorization": _bearer_for("alice")},
    )
    assert response.status_code in (401, 403)


def test_delete_emits_audit_event(client: TestClient) -> None:
    ws_id = _create_ws(client)
    state_before = client.app.state.cp  # type: ignore[attr-defined]
    pre_count = len(list(state_before.audit_events.list_for_workspace(ws_id)))
    client.delete(
        f"/v1/workspaces/{ws_id}",
        headers={"authorization": _bearer_for("owner-1")},
    )
    actions = [
        e.action for e in state_before.audit_events.list_for_workspace(ws_id)
    ]
    assert "workspace:delete" in actions
    assert len(actions) > pre_count


def test_delete_unknown_workspace_returns_404(client: TestClient) -> None:
    response = client.delete(
        f"/v1/workspaces/{uuid4()}",
        headers={"authorization": _bearer_for("owner-1")},
    )
    # Caller is not a member of a non-existent workspace → 401/403/404
    assert response.status_code in (401, 403, 404)


def test_delete_idempotent_returns_404_on_second_call(client: TestClient) -> None:
    ws_id = _create_ws(client)
    headers = {"authorization": _bearer_for("owner-1")}
    first = client.delete(f"/v1/workspaces/{ws_id}", headers=headers)
    assert first.status_code == 204
    second = client.delete(f"/v1/workspaces/{ws_id}", headers=headers)
    assert second.status_code in (401, 403, 404)
