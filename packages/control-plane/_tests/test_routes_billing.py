"""Tests for workspace-scoped billing routes."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from loop_control_plane.app import create_app
from loop_control_plane.paseto import encode_local
from loop_control_plane.usage import UsageEvent

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


@pytest.fixture
def workspace_id(client: TestClient) -> UUID:
    response = client.post(
        "/v1/workspaces",
        headers={"authorization": _bearer_for("owner-1")},
        json={"name": "Acme", "slug": "acme-billing"},
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def test_get_billing_summary_returns_workspace_usage_and_plan(
    client: TestClient,
    workspace_id: UUID,
) -> None:
    state = client.app.state.cp  # type: ignore[attr-defined]
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    state.usage_ledger.append(
        UsageEvent(
            workspace_id=workspace_id,
            metric="messages",
            quantity=42,
            timestamp_ms=now_ms,
        )
    )

    response = client.get(
        f"/v1/workspaces/{workspace_id}/billing",
        headers={"authorization": _bearer_for("owner-1")},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["workspace_id"] == str(workspace_id)
    assert body["plan"]["id"] == "growth"
    assert body["mtd_messages"] == 42
    assert body["mtd_cost_cents"] == 19_900
    assert body["payment_method_last4"] is None
    assert body["customer_portal_url"].endswith(f"/workspaces/{workspace_id}/billing/portal")


def test_get_billing_invoices_returns_current_invoice(
    client: TestClient,
    workspace_id: UUID,
) -> None:
    response = client.get(
        f"/v1/workspaces/{workspace_id}/billing/invoices",
        headers={"authorization": _bearer_for("owner-1")},
    )

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["number"].startswith("LOOP-")
    assert items[0]["amount_cents"] == 19_900
    assert items[0]["pdf_url"].startswith("https://app.loop.dev/billing/invoices/")


def test_update_payment_method_persists_and_audits(
    client: TestClient,
    workspace_id: UUID,
) -> None:
    response = client.post(
        f"/v1/workspaces/{workspace_id}/billing/payment-method",
        headers={"authorization": _bearer_for("owner-1")},
        json={
            "cardholderName": "Ada Lovelace",
            "setup_intent_id": "seti_test_1881_4242",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"last4": "4242"}

    summary = client.get(
        f"/v1/workspaces/{workspace_id}/billing",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert summary.json()["payment_method_last4"] == "4242"

    state = client.app.state.cp  # type: ignore[attr-defined]
    actions = [event.action for event in state.audit_events.list_for_workspace(workspace_id)]
    assert "billing:payment_method:update" in actions


def test_update_payment_method_requires_admin(
    client: TestClient,
    workspace_id: UUID,
) -> None:
    add_member = client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers={"authorization": _bearer_for("owner-1")},
        json={"user_sub": "member-1", "role": "member"},
    )
    assert add_member.status_code == 201, add_member.text

    response = client.post(
        f"/v1/workspaces/{workspace_id}/billing/payment-method",
        headers={"authorization": _bearer_for("member-1")},
        json={"cardholderName": "Ada Lovelace"},
    )

    assert response.status_code in (401, 403)
