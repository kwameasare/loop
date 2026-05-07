"""FastAPI routes for the operator inbox wire-up."""

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


def test_inbox_route_escalate_list_claim_release_resolve(
    client: TestClient, workspace_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    agent_id = uuid4()
    conversation_id = uuid4()

    created = client.post(
        f"/v1/workspaces/{workspace_id}/inbox/escalate",
        headers=headers,
        json={
            "agent_id": str(agent_id),
            "conversation_id": str(conversation_id),
            "user_id": "user-1",
            "reason": "user requested human",
            "last_message_excerpt": "Can a person help?",
            "now_ms": 1_700_000_000_000,
        },
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    listed = client.get(f"/v1/workspaces/{workspace_id}/inbox", headers=headers)
    assert listed.status_code == 200, listed.text
    assert [item["id"] for item in listed.json()["items"]] == [item_id]

    claimed = client.post(
        f"/v1/inbox/{item_id}/claim",
        headers=headers,
        json={"operator_id": "owner-1", "now_ms": 1_700_000_000_100},
    )
    assert claimed.status_code == 200, claimed.text
    assert claimed.json()["status"] == "claimed"

    released = client.post(f"/v1/inbox/{item_id}/release", headers=headers)
    assert released.status_code == 200, released.text
    assert released.json()["status"] == "pending"

    client.post(
        f"/v1/inbox/{item_id}/claim",
        headers=headers,
        json={"operator_id": "owner-1", "now_ms": 1_700_000_000_200},
    )
    resolved = client.post(
        f"/v1/inbox/{item_id}/resolve",
        headers=headers,
        json={"now_ms": 1_700_000_000_300},
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved"


def test_inbox_route_requires_workspace_membership(
    client: TestClient, workspace_id: UUID
) -> None:
    response = client.get(
        f"/v1/workspaces/{workspace_id}/inbox",
        headers={"authorization": _bearer_for("stranger")},
    )
    assert response.status_code in (401, 403)
