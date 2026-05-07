"""Tests for conversation list/read/takeover routes (P0.4)."""

from __future__ import annotations

import asyncio
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
def setup(client: TestClient) -> tuple[UUID, UUID, UUID]:
    """Returns (workspace_id, agent_id, conversation_id) with one
    pre-seeded conversation."""
    headers = {"authorization": _bearer_for("owner-1")}
    ws_id = UUID(
        client.post(
            "/v1/workspaces", headers=headers, json={"name": "Acme", "slug": "acme"}
        ).json()["id"]
    )
    agent_id = UUID(
        client.post(
            "/v1/agents",
            headers={**headers, "x-loop-workspace-id": str(ws_id)},
            json={"name": "Bot", "slug": "bot"},
        ).json()["id"]
    )
    cp = client.app.state.cp  # type: ignore[attr-defined]
    detail = asyncio.run(
        cp.conversations._seed(
            workspace_id=ws_id,
            agent_id=agent_id,
            subject="Where is my order?",
            last_user_message="Where is my order?",
            last_assistant_message="Looking that up now.",
        )
    )
    return ws_id, agent_id, detail.summary.id


def test_list_agent_conversations_returns_seeded_row(
    client: TestClient, setup: tuple[UUID, UUID, UUID]
) -> None:
    _, agent_id, conv_id = setup
    response = client.get(
        f"/v1/agents/{agent_id}/conversations",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == str(conv_id)
    assert items[0]["state"] == "open"


def test_list_filters_by_state(
    client: TestClient, setup: tuple[UUID, UUID, UUID]
) -> None:
    _, agent_id, _ = setup
    closed_resp = client.get(
        f"/v1/agents/{agent_id}/conversations?state=closed",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert closed_resp.json() == {"items": []}


def test_get_conversation_returns_detail(
    client: TestClient, setup: tuple[UUID, UUID, UUID]
) -> None:
    _, _, conv_id = setup
    response = client.get(
        f"/v1/conversations/{conv_id}",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code == 200, response.text
    assert response.json()["last_user_message"] == "Where is my order?"
    assert response.json()["messages"][0]["role"] == "user"


def test_get_unknown_conversation_returns_404(client: TestClient) -> None:
    response = client.get(
        f"/v1/conversations/{uuid4()}",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code == 404


def test_takeover_flips_state_and_sets_operator_taken_over_flag(
    client: TestClient, setup: tuple[UUID, UUID, UUID]
) -> None:
    _, _, conv_id = setup
    response = client.post(
        f"/v1/conversations/{conv_id}/takeover",
        headers={"authorization": _bearer_for("owner-1")},
        json={"note": "User asked for human."},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["state"] == "in-takeover"
    assert body["operator_taken_over"] is True


def test_takeover_requires_admin(
    client: TestClient, setup: tuple[UUID, UUID, UUID]
) -> None:
    workspace_id, _, conv_id = setup
    client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers={"authorization": _bearer_for("owner-1")},
        json={"user_sub": "alice", "role": "member"},
    )
    response = client.post(
        f"/v1/conversations/{conv_id}/takeover",
        headers={"authorization": _bearer_for("alice")},
        json={"note": ""},
    )
    assert response.status_code in (401, 403)


def test_takeover_emits_audit_event(
    client: TestClient, setup: tuple[UUID, UUID, UUID]
) -> None:
    workspace_id, _, conv_id = setup
    client.post(
        f"/v1/conversations/{conv_id}/takeover",
        headers={"authorization": _bearer_for("owner-1")},
        json={"note": "abc"},
    )
    state = client.app.state.cp  # type: ignore[attr-defined]
    actions = [
        e.action for e in state.audit_events.list_for_workspace(workspace_id)
    ]
    assert "conversation:takeover" in actions


def test_takeover_idempotent(
    client: TestClient, setup: tuple[UUID, UUID, UUID]
) -> None:
    _, _, conv_id = setup
    headers = {"authorization": _bearer_for("owner-1")}
    first = client.post(
        f"/v1/conversations/{conv_id}/takeover", headers=headers, json={"note": ""}
    )
    second = client.post(
        f"/v1/conversations/{conv_id}/takeover", headers=headers, json={"note": ""}
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["state"] == "in-takeover"


def test_operator_message_requires_takeover(
    client: TestClient, setup: tuple[UUID, UUID, UUID]
) -> None:
    _, _, conv_id = setup
    response = client.post(
        f"/v1/conversations/{conv_id}/operator-messages",
        headers={"authorization": _bearer_for("owner-1")},
        json={"body": "I can help from here."},
    )
    assert response.status_code == 409


def test_operator_message_appends_to_conversation_and_audit(
    client: TestClient, setup: tuple[UUID, UUID, UUID]
) -> None:
    workspace_id, _, conv_id = setup
    headers = {"authorization": _bearer_for("owner-1")}
    client.post(
        f"/v1/conversations/{conv_id}/takeover",
        headers=headers,
        json={"note": "User asked for human."},
    )
    response = client.post(
        f"/v1/conversations/{conv_id}/operator-messages",
        headers=headers,
        json={"body": "I can help from here."},
    )
    assert response.status_code == 201, response.text
    assert response.json()["role"] == "operator"

    detail = client.get(
        f"/v1/conversations/{conv_id}",
        headers=headers,
    ).json()
    assert detail["messages"][-1]["body"] == "I can help from here."
    actions = [
        e.action
        for e in client.app.state.cp.audit_events.list_for_workspace(workspace_id)  # type: ignore[attr-defined]
    ]
    assert "conversation:operator_message" in actions


def test_handback_returns_control_to_agent(
    client: TestClient, setup: tuple[UUID, UUID, UUID]
) -> None:
    workspace_id, _, conv_id = setup
    headers = {"authorization": _bearer_for("owner-1")}
    client.post(
        f"/v1/conversations/{conv_id}/takeover",
        headers=headers,
        json={"note": "User asked for human."},
    )
    response = client.post(
        f"/v1/conversations/{conv_id}/handback",
        headers=headers,
        json={"note": "Resolved."},
    )
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "open"
    assert response.json()["operator_taken_over"] is False
    actions = [
        e.action
        for e in client.app.state.cp.audit_events.list_for_workspace(workspace_id)  # type: ignore[attr-defined]
    ]
    assert "conversation:handback" in actions


def test_cross_tenant_get_returns_404(
    client: TestClient, setup: tuple[UUID, UUID, UUID]
) -> None:
    """Even a member of another workspace can't read a conversation
    that doesn't belong to them."""
    _, _, conv_id = setup
    headers = {"authorization": _bearer_for("owner-2")}
    # owner-2 creates their own workspace
    client.post(
        "/v1/workspaces", headers=headers, json={"name": "Other", "slug": "other"}
    )
    response = client.get(f"/v1/conversations/{conv_id}", headers=headers)
    # The conversation belongs to owner-1's workspace; owner-2 is not
    # a member there → 401/403/404 (any rejection is fine).
    assert response.status_code in (401, 403, 404)
