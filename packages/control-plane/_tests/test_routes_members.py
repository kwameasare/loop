"""Tests for workspace member CRUD routes (P0.4 + P0.7a).

Hermetic — uses cp's in-memory state + a self-minted PASETO bearer.
"""

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
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def test_list_members_returns_owner_after_create(
    client: TestClient, workspace_id: UUID
) -> None:
    response = client.get(
        f"/v1/workspaces/{workspace_id}/members",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert any(m["user_sub"] == "owner-1" and m["role"] == "owner" for m in items)


def test_add_member_creates_membership(
    client: TestClient, workspace_id: UUID
) -> None:
    response = client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers={"authorization": _bearer_for("owner-1")},
        json={"user_sub": "alice", "role": "member"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["user_sub"] == "alice"
    assert response.json()["role"] == "member"


def test_add_member_requires_owner(
    client: TestClient, workspace_id: UUID
) -> None:
    """A non-owner can't add members. Even another member can't."""
    # First, owner adds a regular member.
    client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers={"authorization": _bearer_for("owner-1")},
        json={"user_sub": "alice", "role": "member"},
    )
    # alice tries to add bob — should fail.
    response = client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers={"authorization": _bearer_for("alice")},
        json={"user_sub": "bob", "role": "member"},
    )
    assert response.status_code in (401, 403)


def test_remove_member_returns_204(
    client: TestClient, workspace_id: UUID
) -> None:
    client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers={"authorization": _bearer_for("owner-1")},
        json={"user_sub": "alice", "role": "member"},
    )
    response = client.delete(
        f"/v1/workspaces/{workspace_id}/members/alice",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code == 204


def test_remove_member_requires_owner(
    client: TestClient, workspace_id: UUID
) -> None:
    client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers={"authorization": _bearer_for("owner-1")},
        json={"user_sub": "alice", "role": "member"},
    )
    response = client.delete(
        f"/v1/workspaces/{workspace_id}/members/alice",
        headers={"authorization": _bearer_for("alice")},
    )
    assert response.status_code in (401, 403)


def test_update_member_role(client: TestClient, workspace_id: UUID) -> None:
    client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers={"authorization": _bearer_for("owner-1")},
        json={"user_sub": "alice", "role": "member"},
    )
    response = client.patch(
        f"/v1/workspaces/{workspace_id}/members/alice",
        headers={"authorization": _bearer_for("owner-1")},
        json={"role": "admin"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["role"] == "admin"


def test_update_member_role_requires_owner(
    client: TestClient, workspace_id: UUID
) -> None:
    client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers={"authorization": _bearer_for("owner-1")},
        json={"user_sub": "alice", "role": "member"},
    )
    response = client.patch(
        f"/v1/workspaces/{workspace_id}/members/alice",
        headers={"authorization": _bearer_for("alice")},
        json={"role": "owner"},
    )
    assert response.status_code in (401, 403)


def test_member_routes_emit_audit_events(
    client: TestClient, workspace_id: UUID
) -> None:
    """P0.7a: every state-changing route writes an audit row."""
    headers = {"authorization": _bearer_for("owner-1")}
    client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers=headers,
        json={"user_sub": "alice", "role": "member"},
    )
    client.patch(
        f"/v1/workspaces/{workspace_id}/members/alice",
        headers=headers,
        json={"role": "admin"},
    )
    client.delete(
        f"/v1/workspaces/{workspace_id}/members/alice",
        headers=headers,
    )
    state = client.app.state.cp  # type: ignore[attr-defined]
    actions = [e.action for e in state.audit_events.list_for_workspace(workspace_id)]
    assert "workspace:member:add" in actions
    assert "workspace:member:role_change" in actions
    assert "workspace:member:remove" in actions


def test_list_members_isolates_workspaces(
    client: TestClient, workspace_id: UUID
) -> None:
    """Non-member can't list members."""
    response = client.get(
        f"/v1/workspaces/{workspace_id}/members",
        headers={"authorization": _bearer_for("stranger")},
    )
    assert response.status_code in (401, 403)
