"""Enterprise signup, workspace invite, and system-admin route tests."""

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
    monkeypatch.setenv("LOOP_SYSTEM_ADMIN_SUBS", "system-admin")


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


def test_enterprise_signup_is_public_and_pending(client: TestClient) -> None:
    response = client.post(
        "/v1/enterprise/signups",
        json={
            "organization_name": "Acme Bank",
            "admin_name": "Maya Chen",
            "admin_email": "maya@example.com",
            "company_size": "1000-5000",
            "region": "na-east",
            "primary_use_case": "Migrate regulated support agents from a legacy platform.",
            "channel_priorities": ["web", "WhatsApp", "voice"],
            "compliance_needs": ["SOC2", "data residency"],
            "sso_required": True,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["signup"]["status"] == "pending_review"
    assert body["signup"]["workspace_slug"] == "acme-bank"
    assert body["next_step"]["href"] == "/login?returnTo=/system/admin"


def test_cp_api_allows_studio_cors_preflight(client: TestClient) -> None:
    response = client.options(
        "/v1/enterprise/signups",
        headers={
            "origin": "http://localhost:13001",
            "access-control-request-method": "POST",
            "access-control-request-headers": "content-type",
        },
    )
    assert response.status_code == 200, response.text
    assert response.headers["access-control-allow-origin"] == "http://localhost:13001"


def test_workspace_invites_are_admin_scoped_and_audited(client: TestClient) -> None:
    created = client.post(
        "/v1/workspaces",
        headers={"authorization": _bearer_for("owner-1")},
        json={"name": "Acme", "slug": "acme"},
    )
    assert created.status_code == 201, created.text
    workspace_id = UUID(created.json()["id"])

    response = client.post(
        f"/v1/workspaces/{workspace_id}/invites",
        headers={"authorization": _bearer_for("owner-1")},
        json={
            "email": "operator@example.com",
            "role": "admin",
            "full_name": "Ops Lead",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["email"] == "operator@example.com"
    assert response.json()["status"] == "pending"

    listed = client.get(
        f"/v1/workspaces/{workspace_id}/invites",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["items"][0]["role"] == "admin"

    state = client.app.state.cp  # type: ignore[attr-defined]
    actions = [e.action for e in state.audit_events.list_for_workspace(workspace_id)]
    assert "workspace:invite:create" in actions


def test_system_admin_approval_provisions_workspace_and_owner_invite(
    client: TestClient,
) -> None:
    signup = client.post(
        "/v1/enterprise/signups",
        json={
            "organization_name": "Globex Support",
            "admin_name": "Dana Ops",
            "admin_email": "dana@example.com",
            "company_size": "500-1000",
            "region": "na-east",
            "primary_use_case": "Launch governed agents across support channels.",
        },
    )
    assert signup.status_code == 201, signup.text
    signup_id = signup.json()["signup"]["id"]

    denied = client.get(
        "/v1/system/admin/overview",
        headers={"authorization": _bearer_for("not-admin")},
    )
    assert denied.status_code in (401, 403)

    approved = client.post(
        f"/v1/system/admin/signups/{signup_id}/approve",
        headers={"authorization": _bearer_for("system-admin")},
        json={"note": "Approved after procurement review."},
    )
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["signup"]["status"] == "approved"
    assert body["admin_invite"]["email"] == "dana@example.com"
    workspace_id = UUID(body["workspace_id"])

    overview = client.get(
        "/v1/system/admin/overview",
        headers={"authorization": _bearer_for("system-admin")},
    )
    assert overview.status_code == 200, overview.text
    assert overview.json()["metrics"]["workspaces"] == 1
    assert overview.json()["metrics"]["pending_invites"] == 1

    state = client.app.state.cp  # type: ignore[attr-defined]
    actions = [e.action for e in state.audit_events.list_for_workspace(workspace_id)]
    assert "workspace:create_from_enterprise_signup" in actions
    assert "workspace:invite:create" in actions
