"""Tests for workspace KB document routes (P0.4)."""

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


def test_list_starts_empty(client: TestClient, workspace_id: UUID) -> None:
    response = client.get(
        f"/v1/workspaces/{workspace_id}/kb/documents",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_create_returns_pending_state(
    client: TestClient, workspace_id: UUID
) -> None:
    response = client.post(
        f"/v1/workspaces/{workspace_id}/kb/documents",
        headers={"authorization": _bearer_for("owner-1")},
        json={"source_url": "https://docs.acme.example/api", "title": "API"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["state"] == "pending"
    assert body["chunk_count"] == 0
    assert body["title"] == "API"


def test_create_idempotent_on_same_url(
    client: TestClient, workspace_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    a = client.post(
        f"/v1/workspaces/{workspace_id}/kb/documents",
        headers=headers,
        json={"source_url": "https://docs.acme.example/api"},
    )
    b = client.post(
        f"/v1/workspaces/{workspace_id}/kb/documents",
        headers=headers,
        json={"source_url": "https://docs.acme.example/api"},
    )
    assert a.json()["id"] == b.json()["id"]


def test_create_requires_admin(client: TestClient, workspace_id: UUID) -> None:
    client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers={"authorization": _bearer_for("owner-1")},
        json={"user_sub": "alice", "role": "member"},
    )
    response = client.post(
        f"/v1/workspaces/{workspace_id}/kb/documents",
        headers={"authorization": _bearer_for("alice")},
        json={"source_url": "https://docs.acme.example/api"},
    )
    assert response.status_code in (401, 403)


def test_delete_returns_204(client: TestClient, workspace_id: UUID) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    doc = client.post(
        f"/v1/workspaces/{workspace_id}/kb/documents",
        headers=headers,
        json={"source_url": "https://docs.acme.example/api"},
    ).json()
    response = client.delete(
        f"/v1/workspaces/{workspace_id}/kb/documents/{doc['id']}",
        headers=headers,
    )
    assert response.status_code == 204


def test_delete_unknown_returns_404(
    client: TestClient, workspace_id: UUID
) -> None:
    response = client.delete(
        f"/v1/workspaces/{workspace_id}/kb/documents/{uuid4()}",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code == 404


def test_refresh_all_marks_documents_ingesting(
    client: TestClient, workspace_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    client.post(
        f"/v1/workspaces/{workspace_id}/kb/documents",
        headers=headers,
        json={"source_url": "https://a.example/"},
    )
    client.post(
        f"/v1/workspaces/{workspace_id}/kb/documents",
        headers=headers,
        json={"source_url": "https://b.example/"},
    )
    response = client.post(
        f"/v1/workspaces/{workspace_id}/kb/refresh", headers=headers
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert len(items) == 2
    assert all(i["state"] == "ingesting" for i in items)
    assert all(i["last_refreshed_at"] is not None for i in items)


def test_kb_routes_emit_audit_events(
    client: TestClient, workspace_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    doc = client.post(
        f"/v1/workspaces/{workspace_id}/kb/documents",
        headers=headers,
        json={"source_url": "https://x.example/"},
    ).json()
    client.post(f"/v1/workspaces/{workspace_id}/kb/refresh", headers=headers)
    client.delete(
        f"/v1/workspaces/{workspace_id}/kb/documents/{doc['id']}",
        headers=headers,
    )
    state = client.app.state.cp  # type: ignore[attr-defined]
    actions = [e.action for e in state.audit_events.list_for_workspace(workspace_id)]
    assert "kb:document:create" in actions
    assert "kb:refresh_all" in actions
    assert "kb:document:delete" in actions


def test_cross_tenant_isolation(client: TestClient) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    a_id = UUID(
        client.post(
            "/v1/workspaces", headers=headers, json={"name": "A", "slug": "a"}
        ).json()["id"]
    )
    b_id = UUID(
        client.post(
            "/v1/workspaces", headers=headers, json={"name": "B", "slug": "b"}
        ).json()["id"]
    )
    client.post(
        f"/v1/workspaces/{a_id}/kb/documents",
        headers=headers,
        json={"source_url": "https://a.example/"},
    )
    a_list = client.get(
        f"/v1/workspaces/{a_id}/kb/documents", headers=headers
    ).json()["items"]
    b_list = client.get(
        f"/v1/workspaces/{b_id}/kb/documents", headers=headers
    ).json()["items"]
    assert len(a_list) == 1
    assert b_list == []
