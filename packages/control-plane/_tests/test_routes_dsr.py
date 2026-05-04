"""Tests for the GDPR DSR routes (P0.8b).

Hermetic — uses cp's in-memory state + a self-minted PASETO bearer
token so we don't have to spin up the full IdP exchange flow.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from loop_control_plane.app import create_app
from loop_control_plane.data_deletion import DataDeletionState
from loop_control_plane.paseto import encode_local
from loop_control_plane.workspaces import WorkspaceService

# 32-byte test PASETO key (cp requires len>=32).
_TEST_KEY = b"x" * 32


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the PASETO key so caller_sub() validates."""
    monkeypatch.setenv("LOOP_CP_PASETO_LOCAL_KEY", _TEST_KEY.decode())
    monkeypatch.setenv("LOOP_OTEL_ENDPOINT", "disabled")


def _bearer_for(sub: str) -> str:
    """Mint a PASETO bearer for `sub`."""
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    token = encode_local(
        claims={"sub": sub},
        key=_TEST_KEY,
        now_ms=now_ms,
        expires_in_ms=3600 * 1000,
    )
    return f"Bearer {token}"


@pytest.fixture
def client(env: None) -> TestClient:
    app = create_app()
    return TestClient(app)


@pytest.fixture
async def workspace_id(client: TestClient) -> UUID:
    """Create a workspace owned by ``owner-1`` and return its id."""
    response = client.post(
        "/v1/workspaces",
        headers={"authorization": _bearer_for("owner-1")},
        json={"name": "Acme", "slug": "acme"},
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


@pytest.mark.asyncio
async def test_enqueue_deletion_returns_pending_request(
    client: TestClient, workspace_id: UUID
) -> None:
    response = client.post(
        f"/v1/workspaces/{workspace_id}/data-deletion",
        headers={"authorization": _bearer_for("owner-1")},
        json={"requested_by_email": "owner@example.com"},
    )
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["state"] == DataDeletionState.PENDING.value
    assert body["workspace_id"] == str(workspace_id)
    assert body["requested_by_email"] == "owner@example.com"
    assert body["completed_at"] is None


@pytest.mark.asyncio
async def test_enqueue_deletion_is_idempotent_for_pending(
    client: TestClient, workspace_id: UUID
) -> None:
    """A second POST while a pending request exists returns the same
    request id."""
    headers = {"authorization": _bearer_for("owner-1")}
    body = {"requested_by_email": "owner@example.com"}
    first = client.post(
        f"/v1/workspaces/{workspace_id}/data-deletion", headers=headers, json=body
    )
    second = client.post(
        f"/v1/workspaces/{workspace_id}/data-deletion", headers=headers, json=body
    )
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]


@pytest.mark.asyncio
async def test_enqueue_requires_owner_role(
    client: TestClient, workspace_id: UUID
) -> None:
    """A different user (not workspace owner) gets 403."""
    response = client.post(
        f"/v1/workspaces/{workspace_id}/data-deletion",
        headers={"authorization": _bearer_for("not-the-owner")},
        json={"requested_by_email": "x@example.com"},
    )
    # `authorize_workspace_access` raises an `AuthorisationError` for
    # missing role; the cp app's domain_error handler maps it to a
    # LOOP-API code with status 403.
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_enqueue_rejects_invalid_email(
    client: TestClient, workspace_id: UUID
) -> None:
    response = client.post(
        f"/v1/workspaces/{workspace_id}/data-deletion",
        headers={"authorization": _bearer_for("owner-1")},
        json={"requested_by_email": "not-an-email"},
    )
    # Pydantic returns 422 on EmailStr validation failure.
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_returns_existing_requests(
    client: TestClient, workspace_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    client.post(
        f"/v1/workspaces/{workspace_id}/data-deletion",
        headers=headers,
        json={"requested_by_email": "owner@example.com"},
    )
    response = client.get(
        f"/v1/workspaces/{workspace_id}/data-deletion", headers=headers
    )
    assert response.status_code == 200, response.text
    requests_list = response.json()["requests"]
    assert len(requests_list) == 1
    assert requests_list[0]["state"] == DataDeletionState.PENDING.value


@pytest.mark.asyncio
async def test_get_returns_specific_request(
    client: TestClient, workspace_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    enqueue = client.post(
        f"/v1/workspaces/{workspace_id}/data-deletion",
        headers=headers,
        json={"requested_by_email": "owner@example.com"},
    )
    request_id = enqueue.json()["id"]
    response = client.get(
        f"/v1/workspaces/{workspace_id}/data-deletion/{request_id}", headers=headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["id"] == request_id


@pytest.mark.asyncio
async def test_get_returns_404_for_unknown_id(
    client: TestClient, workspace_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    response = client.get(
        f"/v1/workspaces/{workspace_id}/data-deletion/{uuid4()}",
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_isolates_across_workspaces(
    client: TestClient, workspace_id: UUID
) -> None:
    """A request belonging to workspace A must not leak through a
    GET against workspace B's URL even if the caller is a member of A."""
    headers = {"authorization": _bearer_for("owner-1")}
    enqueue = client.post(
        f"/v1/workspaces/{workspace_id}/data-deletion",
        headers=headers,
        json={"requested_by_email": "owner@example.com"},
    )
    request_id = enqueue.json()["id"]

    # Create a second workspace; same owner.
    other_resp = client.post(
        "/v1/workspaces",
        headers=headers,
        json={"name": "Other", "slug": "other"},
    )
    other_id = UUID(other_resp.json()["id"])

    response = client.get(
        f"/v1/workspaces/{other_id}/data-deletion/{request_id}", headers=headers
    )
    # Even though the caller has access to BOTH workspaces, the
    # request id doesn't belong to `other_id` → 404.
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_enqueue_writes_audit_event(
    client: TestClient, workspace_id: UUID
) -> None:
    """SOC2 CC7.3: enqueue must produce an audit row with actor + action."""
    headers = {"authorization": _bearer_for("owner-1")}
    client.post(
        f"/v1/workspaces/{workspace_id}/data-deletion",
        headers=headers,
        json={"requested_by_email": "owner@example.com"},
    )
    # Read audit log directly from app state.
    state = client.app.state.cp  # type: ignore[attr-defined]
    events = list(state.audit_events.list_for_workspace(workspace_id))
    actions = [e.action for e in events]
    assert "workspace:data_deletion:enqueue" in actions
