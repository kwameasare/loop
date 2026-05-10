"""Tests for workspace-scoped enterprise SAML configuration routes."""

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
        json={"name": "Acme", "slug": "acme"},
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def test_get_saml_config_returns_default_not_configured(
    client: TestClient,
    workspace_id: UUID,
) -> None:
    response = client.get(
        f"/v1/workspaces/{workspace_id}/enterprise/saml",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "not_configured"
    assert body["entity_id"] is None
    assert body["connected_at"] is None
    assert body["acs_url"].endswith(f"/auth/saml/acs/{workspace_id}")


def test_post_saml_config_with_metadata_url_persists_and_audits(
    client: TestClient,
    workspace_id: UUID,
) -> None:
    response = client.post(
        f"/v1/workspaces/{workspace_id}/enterprise/saml",
        headers={"authorization": _bearer_for("owner-1")},
        json={"metadata_url": "https://idp.example.test/metadata"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "pending_verification"
    assert body["entity_id"] == "https://idp.example.test/metadata"
    assert body["metadata_source"] == "metadata_url"

    stored = client.get(
        f"/v1/workspaces/{workspace_id}/enterprise/saml",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert stored.json()["entity_id"] == "https://idp.example.test/metadata"

    state = client.app.state.cp  # type: ignore[attr-defined]
    actions = [event.action for event in state.audit_events.list_for_workspace(workspace_id)]
    assert "enterprise_saml:update" in actions


def test_post_saml_config_extracts_entity_id_from_xml(
    client: TestClient,
    workspace_id: UUID,
) -> None:
    metadata = (
        '<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata" '
        'entityID="https://idp.example.test/entity"></EntityDescriptor>'
    )
    response = client.post(
        f"/v1/workspaces/{workspace_id}/enterprise/saml",
        headers={"authorization": _bearer_for("owner-1")},
        json={"metadata_xml": metadata},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "pending_verification"
    assert body["entity_id"] == "https://idp.example.test/entity"
    assert body["metadata_source"] == "metadata_xml"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {
            "metadata_url": "https://idp.example.test/metadata",
            "metadata_xml": "<EntityDescriptor/>",
        },
        {"metadata_url": "ftp://idp.example.test/metadata"},
        {"metadata_xml": "<not xml"},
    ],
)
def test_post_saml_config_rejects_invalid_metadata(
    client: TestClient,
    workspace_id: UUID,
    payload: dict[str, str],
) -> None:
    response = client.post(
        f"/v1/workspaces/{workspace_id}/enterprise/saml",
        headers={"authorization": _bearer_for("owner-1")},
        json=payload,
    )
    assert response.status_code in (400, 422), response.text


def test_post_saml_config_requires_admin(
    client: TestClient,
    workspace_id: UUID,
) -> None:
    client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers={"authorization": _bearer_for("owner-1")},
        json={"user_sub": "alice", "role": "member"},
    )
    response = client.post(
        f"/v1/workspaces/{workspace_id}/enterprise/saml",
        headers={"authorization": _bearer_for("alice")},
        json={"metadata_url": "https://idp.example.test/metadata"},
    )
    assert response.status_code in (401, 403)
