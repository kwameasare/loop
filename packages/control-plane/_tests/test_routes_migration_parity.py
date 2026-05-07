"""Tests for the migration parity workspace route."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from loop_control_plane.app import create_app
from loop_control_plane.paseto import encode_local
from loop_control_plane.trace_search import TraceSummary

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


@pytest.fixture
def client(env: None) -> TestClient:
    return TestClient(create_app())


def _workspace(client: TestClient) -> UUID:
    return UUID(
        client.post(
            "/v1/workspaces",
            headers={"authorization": _bearer_for("owner-1")},
            json={"name": "Acme", "slug": "acme"},
        ).json()["id"]
    )


def _agent(client: TestClient, workspace_id: UUID) -> UUID:
    response = client.post(
        "/v1/agents",
        headers={
            "authorization": _bearer_for("owner-1"),
            "x-loop-workspace-id": str(workspace_id),
        },
        json={"name": "Support Bot", "slug": "support-bot"},
    )
    return UUID(response.json()["id"])


def test_migration_parity_derives_readiness_from_agent_version_and_traces(
    client: TestClient,
) -> None:
    workspace_id = _workspace(client)
    agent_id = _agent(client, workspace_id)
    headers = {"authorization": _bearer_for("owner-1")}
    client.post(
        f"/v1/agents/{agent_id}/versions",
        headers=headers,
        json={
            "spec": {
                "system_prompt": "Preserve imported refund behavior.",
                "tools": ["lookup_order", "issue_refund"],
                "migration": {
                    "archive": "acme.bpz",
                    "archive_sha": "sha256:" + ("a" * 64),
                },
            }
        },
    )
    cp = client.app.state.cp  # type: ignore[attr-defined]
    cp.trace_store.add(
        TraceSummary(
            workspace_id=workspace_id,
            trace_id="b" * 32,
            turn_id=uuid4(),
            conversation_id=uuid4(),
            agent_id=agent_id,
            started_at=datetime(2026, 5, 4, 11, 0, tzinfo=UTC),
            duration_ms=100,
            span_count=3,
        )
    )

    response = client.get(
        f"/v1/workspaces/{workspace_id}/migration/parity",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["lineage"]["archive"] == "acme.bpz"
    assert body["readiness"]["parityPassing"] == 1
    assert any(diff["id"] == "diff_risk_tools" for diff in body["diffs"])
    assert any(repair["id"] == "rep_tool_safety_contract" for repair in body["repairs"])
    assert body["cutover"]["rollbackTriggers"][0]["metric"] == "regression"


def test_migration_parity_requires_workspace_membership(
    client: TestClient,
) -> None:
    workspace_id = _workspace(client)

    response = client.get(
        f"/v1/workspaces/{workspace_id}/migration/parity",
        headers={"authorization": _bearer_for("stranger")},
    )

    assert response.status_code in (401, 403)
