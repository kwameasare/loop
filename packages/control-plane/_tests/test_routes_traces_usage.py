"""Tests for trace search + usage list routes (P0.4)."""

from __future__ import annotations

from datetime import UTC, datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from loop_control_plane.app import create_app
from loop_control_plane.paseto import encode_local
from loop_control_plane.trace_search import InMemoryTraceStore, TraceSummary
from loop_control_plane.usage import UsageEvent

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
    return UUID(response.json()["id"])


# --------------------------------------------------------------------------- #
# Traces                                                                      #
# --------------------------------------------------------------------------- #


def test_search_traces_returns_empty_for_new_workspace(
    client: TestClient, workspace_id: UUID
) -> None:
    response = client.get(
        f"/v1/workspaces/{workspace_id}/traces",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"items": [], "next_cursor": None}


def test_search_traces_filters_by_workspace(
    client: TestClient, workspace_id: UUID
) -> None:
    """Trace from another workspace must NOT leak."""
    cp = client.app.state.cp  # type: ignore[attr-defined]
    other_ws = uuid4()
    cp.trace_store.add(
        TraceSummary(
            workspace_id=other_ws,
            trace_id="a" * 32,
            turn_id=uuid4(),
            conversation_id=uuid4(),
            agent_id=uuid4(),
            started_at=datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc),
            duration_ms=100,
            span_count=3,
        )
    )
    cp.trace_store.add(
        TraceSummary(
            workspace_id=workspace_id,
            trace_id="b" * 32,
            turn_id=uuid4(),
            conversation_id=uuid4(),
            agent_id=uuid4(),
            started_at=datetime(2026, 5, 4, 11, 0, tzinfo=timezone.utc),
            duration_ms=100,
            span_count=3,
        )
    )
    response = client.get(
        f"/v1/workspaces/{workspace_id}/traces",
        headers={"authorization": _bearer_for("owner-1")},
    )
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["trace_id"] == "b" * 32
    assert items[0]["workspace_id"] == str(workspace_id)


def test_search_traces_supports_only_errors_filter(
    client: TestClient, workspace_id: UUID
) -> None:
    cp = client.app.state.cp  # type: ignore[attr-defined]
    for i, has_error in enumerate([True, False, True]):
        cp.trace_store.add(
            TraceSummary(
                workspace_id=workspace_id,
                trace_id=f"{i}" * 32,
                turn_id=uuid4(),
                conversation_id=uuid4(),
                agent_id=uuid4(),
                started_at=datetime(2026, 5, 4, 10 + i, 0, tzinfo=timezone.utc),
                duration_ms=100,
                span_count=3,
                error=has_error,
            )
        )
    response = client.get(
        f"/v1/workspaces/{workspace_id}/traces?only_errors=true",
        headers={"authorization": _bearer_for("owner-1")},
    )
    items = response.json()["items"]
    assert len(items) == 2
    assert all(i["error"] is True for i in items)


def test_search_traces_requires_workspace_membership(
    client: TestClient, workspace_id: UUID
) -> None:
    response = client.get(
        f"/v1/workspaces/{workspace_id}/traces",
        headers={"authorization": _bearer_for("stranger")},
    )
    assert response.status_code in (401, 403)


def test_search_traces_rejects_invalid_window(
    client: TestClient, workspace_id: UUID
) -> None:
    """started_at_from must be <= started_at_to per the model
    validator; the route maps the resulting ValueError to 400."""
    response = client.get(
        f"/v1/workspaces/{workspace_id}/traces"
        "?started_at_from=2026-05-04T12:00:00%2B00:00"
        "&started_at_to=2026-05-04T11:00:00%2B00:00",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code == 400


# --------------------------------------------------------------------------- #
# Usage                                                                       #
# --------------------------------------------------------------------------- #


def test_list_usage_returns_window_events(
    client: TestClient, workspace_id: UUID
) -> None:
    cp = client.app.state.cp  # type: ignore[attr-defined]
    cp.usage_ledger.append(
        UsageEvent(
            workspace_id=workspace_id,
            metric="input_tokens",
            quantity=1000,
            timestamp_ms=1700000000000,
        )
    )
    cp.usage_ledger.append(
        UsageEvent(
            workspace_id=workspace_id,
            metric="output_tokens",
            quantity=500,
            timestamp_ms=1700000060000,
        )
    )
    response = client.get(
        f"/v1/workspaces/{workspace_id}/usage"
        f"?start_ms=1700000000000&end_ms=1700000099999",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert len(items) == 2
    metrics = {i["metric"] for i in items}
    assert metrics == {"input_tokens", "output_tokens"}


def test_list_usage_filters_by_workspace(
    client: TestClient, workspace_id: UUID
) -> None:
    cp = client.app.state.cp  # type: ignore[attr-defined]
    cp.usage_ledger.append(
        UsageEvent(
            workspace_id=workspace_id,
            metric="input_tokens",
            quantity=1000,
            timestamp_ms=1700000000000,
        )
    )
    other_ws = uuid4()
    cp.usage_ledger.append(
        UsageEvent(
            workspace_id=other_ws,
            metric="input_tokens",
            quantity=99999,
            timestamp_ms=1700000000000,
        )
    )
    response = client.get(
        f"/v1/workspaces/{workspace_id}/usage"
        f"?start_ms=1700000000000&end_ms=1700001000000",
        headers={"authorization": _bearer_for("owner-1")},
    )
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["workspace_id"] == str(workspace_id)


def test_list_usage_requires_membership(
    client: TestClient, workspace_id: UUID
) -> None:
    response = client.get(
        f"/v1/workspaces/{workspace_id}/usage?start_ms=0&end_ms=1",
        headers={"authorization": _bearer_for("stranger")},
    )
    assert response.status_code in (401, 403)


def test_list_usage_rejects_inverted_window(
    client: TestClient, workspace_id: UUID
) -> None:
    response = client.get(
        f"/v1/workspaces/{workspace_id}/usage?start_ms=100&end_ms=50",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code == 400
