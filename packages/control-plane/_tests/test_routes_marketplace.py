"""Tests for the marketplace browse route."""

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


def test_marketplace_browse_returns_first_party_catalog(client: TestClient) -> None:
    response = client.get(
        "/v1/marketplace",
        headers={"authorization": _bearer_for("owner-1")},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["items"]) >= 1
    assert body["items"][0]["install_button_enabled"] is True
    assert "latest_version" in body["items"][0]


def test_marketplace_browse_filters_by_query(client: TestClient) -> None:
    response = client.get(
        "/v1/marketplace?q=salesforce",
        headers={"authorization": _bearer_for("owner-1")},
    )

    assert response.status_code == 200, response.text
    slugs = [item["slug"] for item in response.json()["items"]]
    assert slugs == ["salesforce"]


def test_private_marketplace_publish_version_install_and_deprecate(
    client: TestClient,
) -> None:
    workspace = client.post(
        "/v1/workspaces",
        headers={"authorization": _bearer_for("owner-1")},
        json={"name": "Acme", "slug": f"acme-{uuid4().hex[:8]}"},
    )
    assert workspace.status_code == 201, workspace.text
    workspace_id = UUID(workspace.json()["id"])

    published = client.post(
        "/v1/marketplace/items",
        headers={"authorization": _bearer_for("owner-1")},
        json={
            "workspace_id": str(workspace_id),
            "name": "Private refund skill",
            "slug": f"private-refunds-{uuid4().hex[:8]}",
            "description": "Internal refund policy helper",
            "category": "skills",
            "visibility": "private",
            "version": "1.0.0",
            "artifact": {"kind": "skill", "entrypoint": "refunds"},
        },
    )
    assert published.status_code == 201, published.text
    item_id = published.json()["id"]
    assert published.json()["latest_version"] == "1.0.0"

    version = client.post(
        f"/v1/marketplace/items/{item_id}/versions",
        headers={"authorization": _bearer_for("owner-1")},
        json={
            "workspace_id": str(workspace_id),
            "version": "1.1.0",
            "changelog": "Adds stricter refund evidence.",
            "artifact": {"kind": "skill", "entrypoint": "refunds.v2"},
        },
    )
    assert version.status_code == 201, version.text
    assert version.json()["latest_version"] == "1.1.0"

    install = client.post(
        f"/v1/marketplace/items/{item_id}/install",
        headers={"authorization": _bearer_for("owner-1")},
        json={"workspace_id": str(workspace_id)},
    )
    assert install.status_code == 201, install.text
    assert install.json()["audit_ref"].startswith("marketplace.install.")

    installs = client.get(
        f"/v1/marketplace/items/{item_id}/installs?workspace_id={workspace_id}",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert installs.status_code == 200, installs.text
    assert installs.json()["items"][0]["item_id"] == item_id

    deprecated = client.post(
        f"/v1/marketplace/items/{item_id}/deprecate",
        headers={"authorization": _bearer_for("owner-1")},
        json={"workspace_id": str(workspace_id), "reason": "Superseded by v2 template"},
    )
    assert deprecated.status_code == 200, deprecated.text
    assert deprecated.json()["lifecycle"] == "deprecated"
