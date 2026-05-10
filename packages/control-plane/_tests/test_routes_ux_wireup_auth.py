"""Authorization tests for canonical UX wire-up routes."""

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
        claims={"sub": sub},
        key=_TEST_KEY,
        now_ms=now_ms,
        expires_in_ms=3600 * 1000,
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
        json={"name": "Acme", "slug": f"acme-{uuid4().hex[:8]}", "region": "eu-west"},
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


@pytest.fixture
def agent_id(client: TestClient, workspace_id: UUID) -> UUID:
    response = client.post(
        "/v1/agents",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"name": "Support Bot", "slug": f"support-{uuid4().hex[:8]}"},
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


def test_members_cannot_create_or_approve_governed_ux_artifacts(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
    member_auth: dict[str, str],
) -> None:
    create_changeset = client.post(
        f"/v1/workspaces/{workspace_id}/approval-changesets",
        headers=member_auth,
        json={"title": "Member change", "payload": {"prompt": "unsafe edit"}},
    )
    assert create_changeset.status_code == 403, create_changeset.text

    changeset = client.post(
        f"/v1/workspaces/{workspace_id}/approval-changesets",
        headers=_auth(),
        json={"title": "Admin change", "payload": {"prompt": "safe edit"}},
    )
    assert changeset.status_code == 201, changeset.text
    changeset_id = changeset.json()["id"]

    approve = client.post(
        f"/v1/workspaces/{workspace_id}/approval-changesets/{changeset_id}/approve",
        headers=member_auth,
    )
    assert approve.status_code == 403, approve.text

    edit = client.post(
        f"/v1/workspaces/{workspace_id}/approval-changesets/{changeset_id}/edit",
        headers=member_auth,
        json={"title": "Member edit", "payload": {"prompt": "changed after approval"}},
    )
    assert edit.status_code == 403, edit.text

    comment_resolution = client.post(
        f"/v1/agents/{agent_id}/comments/cmt_123/resolve",
        headers=member_auth,
        json={
            "expected_behavior": "Escalate legal threats before answering.",
            "failure_reason": "The current answer missed the legal escalation.",
            "also_create_eval_case": True,
            "source_trace": "trace_legal",
        },
    )
    assert comment_resolution.status_code == 403, comment_resolution.text


def test_members_cannot_create_export_or_external_resource_ux_artifacts(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
    member_auth: dict[str, str],
) -> None:
    requests = [
        (
            f"/v1/workspaces/{workspace_id}/shares",
            {
                "source_type": "trace",
                "source_id": "trace_refund_123",
                "redactions": ["pii", "secrets"],
            },
        ),
        (
            f"/v1/workspaces/{workspace_id}/voice/demo-links",
            {"snapshot_id": "snap_refund_123", "expires_in_minutes": 5},
        ),
        (
            f"/v1/workspaces/{workspace_id}/voice/numbers/provision",
            {"country": "US", "area_code": "415", "provider": "twilio"},
        ),
        (
            f"/v1/workspaces/{workspace_id}/pair-debug/audio/session",
            {"agent_id": str(agent_id), "participant_id": "bob"},
        ),
        (
            f"/v1/workspaces/{workspace_id}/scenes",
            {
                "name": "Legal threat escalation",
                "category": "escalation",
                "trace_ids": ["trace_refund_123"],
                "expected_behavior": "Escalate before refund policy advice.",
            },
        ),
    ]
    for path, json_body in requests:
        response = client.post(path, headers=member_auth, json=json_body)
        assert response.status_code == 403, f"{path}: {response.text}"


def test_members_can_still_read_and_replay_shared_ux_artifacts(
    client: TestClient,
    workspace_id: UUID,
    member_auth: dict[str, str],
) -> None:
    scene = client.post(
        f"/v1/workspaces/{workspace_id}/scenes",
        headers=_auth(),
        json={
            "name": "Refund policy parity",
            "category": "refund",
            "trace_ids": ["trace_refund_123"],
            "expected_behavior": "Quote the current refund window.",
        },
    )
    assert scene.status_code == 201, scene.text

    listed = client.get(f"/v1/workspaces/{workspace_id}/scenes", headers=member_auth)
    assert listed.status_code == 200, listed.text
    assert listed.json()["items"][0]["id"] == scene.json()["id"]

    replay = client.post(
        f"/v1/workspaces/{workspace_id}/scenes/{scene.json()['id']}/replay",
        headers=member_auth,
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["status"] == "queued"


def test_dashboard_visibility_and_mutation_are_owner_scoped(
    client: TestClient,
    workspace_id: UUID,
    member_auth: dict[str, str],
) -> None:
    private_dashboard = client.post(
        f"/v1/workspaces/{workspace_id}/dashboards",
        headers=_auth(),
        json={
            "name": "Owner private",
            "layout": [{"metric_id": "p95_latency", "span": 4}],
            "shared_with": [],
        },
    )
    assert private_dashboard.status_code == 201, private_dashboard.text
    private_id = private_dashboard.json()["id"]

    hidden_list = client.get(
        f"/v1/workspaces/{workspace_id}/dashboards",
        headers=member_auth,
    )
    assert hidden_list.status_code == 200, hidden_list.text
    assert hidden_list.json()["items"] == []

    private_update = client.patch(
        f"/v1/workspaces/{workspace_id}/dashboards/{private_id}",
        headers=member_auth,
        json={
            "name": "Member takeover",
            "layout": [{"metric_id": "spend", "span": 6}],
            "shared_with": [],
        },
    )
    assert private_update.status_code == 403, private_update.text

    private_delete = client.delete(
        f"/v1/workspaces/{workspace_id}/dashboards/{private_id}",
        headers=member_auth,
    )
    assert private_delete.status_code == 403, private_delete.text

    shared_dashboard = client.post(
        f"/v1/workspaces/{workspace_id}/dashboards",
        headers=_auth(),
        json={
            "name": "Shared production health",
            "layout": [{"metric_id": "escalations", "span": 3}],
            "shared_with": ["alice"],
        },
    )
    assert shared_dashboard.status_code == 201, shared_dashboard.text
    shared_id = shared_dashboard.json()["id"]

    visible_list = client.get(
        f"/v1/workspaces/{workspace_id}/dashboards",
        headers=member_auth,
    )
    assert visible_list.status_code == 200, visible_list.text
    assert [item["id"] for item in visible_list.json()["items"]] == [shared_id]

    shared_update = client.patch(
        f"/v1/workspaces/{workspace_id}/dashboards/{shared_id}",
        headers=member_auth,
        json={
            "name": "Shared takeover",
            "layout": [{"metric_id": "spend", "span": 6}],
            "shared_with": ["alice"],
        },
    )
    assert shared_update.status_code == 403, shared_update.text

    member_dashboard = client.post(
        f"/v1/workspaces/{workspace_id}/dashboards",
        headers=member_auth,
        json={
            "name": "My work queue",
            "layout": [{"metric_id": "blocked_deploys", "span": 4}],
            "shared_with": [],
        },
    )
    assert member_dashboard.status_code == 201, member_dashboard.text
    member_id = member_dashboard.json()["id"]

    member_update = client.patch(
        f"/v1/workspaces/{workspace_id}/dashboards/{member_id}",
        headers=member_auth,
        json={
            "name": "My active work queue",
            "layout": [{"metric_id": "blocked_deploys", "span": 8}],
            "shared_with": ["owner-1"],
        },
    )
    assert member_update.status_code == 200, member_update.text
    assert member_update.json()["layout"][0]["span"] == 8

    member_delete = client.delete(
        f"/v1/workspaces/{workspace_id}/dashboards/{member_id}",
        headers=member_auth,
    )
    assert member_delete.status_code == 204, member_delete.text
