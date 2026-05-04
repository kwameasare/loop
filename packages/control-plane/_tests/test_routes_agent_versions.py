"""Tests for agent version routes (P0.4)."""

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
        json={"name": "Support Bot", "slug": "support-bot", "description": "Helps users"},
    )
    return UUID(response.json()["id"])


def test_list_versions_starts_empty(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    response = client.get(
        f"/v1/agents/{agent_id}/versions",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"items": []}


def test_create_version_assigns_monotonic_numbers(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    v1 = client.post(
        f"/v1/agents/{agent_id}/versions",
        headers=headers,
        json={"spec": {"prompt": "v1"}},
    ).json()
    v2 = client.post(
        f"/v1/agents/{agent_id}/versions",
        headers=headers,
        json={"spec": {"prompt": "v2"}, "notes": "promote me"},
    ).json()
    assert v1["version"] == 1
    assert v2["version"] == 2
    assert v2["notes"] == "promote me"


def test_create_version_requires_admin(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    """Add a regular member; they can list but not create."""
    client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers={"authorization": _bearer_for("owner-1")},
        json={"user_sub": "alice", "role": "member"},
    )
    list_resp = client.get(
        f"/v1/agents/{agent_id}/versions",
        headers={"authorization": _bearer_for("alice")},
    )
    assert list_resp.status_code == 200
    create_resp = client.post(
        f"/v1/agents/{agent_id}/versions",
        headers={"authorization": _bearer_for("alice")},
        json={"spec": {}},
    )
    assert create_resp.status_code in (401, 403)


def test_promote_sets_active_version(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    client.post(
        f"/v1/agents/{agent_id}/versions", headers=headers, json={"spec": {}}
    ).json()
    v2 = client.post(
        f"/v1/agents/{agent_id}/versions", headers=headers, json={"spec": {}}
    ).json()
    promote_resp = client.post(
        f"/v1/agents/{agent_id}/versions/{v2['id']}/promote", headers=headers
    )
    assert promote_resp.status_code == 200, promote_resp.text
    assert promote_resp.json()["active_version"] == 2


def test_promote_idempotent(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    v = client.post(
        f"/v1/agents/{agent_id}/versions", headers=headers, json={"spec": {}}
    ).json()
    client.post(f"/v1/agents/{agent_id}/versions/{v['id']}/promote", headers=headers)
    second = client.post(
        f"/v1/agents/{agent_id}/versions/{v['id']}/promote", headers=headers
    )
    assert second.status_code == 200


def test_promote_unknown_version_returns_404(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    response = client.post(
        f"/v1/agents/{agent_id}/versions/{uuid4()}/promote",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code == 404


def test_promote_emits_audit_event(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    v = client.post(
        f"/v1/agents/{agent_id}/versions", headers=headers, json={"spec": {}}
    ).json()
    client.post(f"/v1/agents/{agent_id}/versions/{v['id']}/promote", headers=headers)
    state = client.app.state.cp  # type: ignore[attr-defined]
    actions = [e.action for e in state.audit_events.list_for_workspace(workspace_id)]
    assert "agent:version:create" in actions
    assert "agent:version:promote" in actions


def test_versions_isolated_across_workspaces(client: TestClient) -> None:
    """Two workspaces with their own agents can share version numbers
    starting at 1; promotion in one doesn't affect the other."""
    headers = {"authorization": _bearer_for("owner-1")}
    ws_a = UUID(
        client.post(
            "/v1/workspaces", headers=headers, json={"name": "A", "slug": "a"}
        ).json()["id"]
    )
    ws_b = UUID(
        client.post(
            "/v1/workspaces", headers=headers, json={"name": "B", "slug": "b"}
        ).json()["id"]
    )
    agent_a = UUID(
        client.post(
            "/v1/agents",
            headers={**headers, "x-loop-workspace-id": str(ws_a)},
            json={"name": "A1", "slug": "a1"},
        ).json()["id"]
    )
    agent_b = UUID(
        client.post(
            "/v1/agents",
            headers={**headers, "x-loop-workspace-id": str(ws_b)},
            json={"name": "B1", "slug": "b1"},
        ).json()["id"]
    )
    client.post(
        f"/v1/agents/{agent_a}/versions", headers=headers, json={"spec": {}}
    )
    client.post(
        f"/v1/agents/{agent_b}/versions", headers=headers, json={"spec": {}}
    )
    a_versions = client.get(
        f"/v1/agents/{agent_a}/versions", headers=headers
    ).json()["items"]
    b_versions = client.get(
        f"/v1/agents/{agent_b}/versions", headers=headers
    ).json()["items"]
    assert a_versions[0]["agent_id"] == str(agent_a)
    assert b_versions[0]["agent_id"] == str(agent_b)
    assert a_versions[0]["version"] == 1
    assert b_versions[0]["version"] == 1
