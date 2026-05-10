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


def test_private_marketplace_items_are_workspace_scoped(
    client: TestClient,
) -> None:
    workspace_one = client.post(
        "/v1/workspaces",
        headers={"authorization": _bearer_for("owner-1")},
        json={"name": "Acme", "slug": f"acme-{uuid4().hex[:8]}"},
    )
    assert workspace_one.status_code == 201, workspace_one.text
    workspace_one_id = UUID(workspace_one.json()["id"])

    workspace_two = client.post(
        "/v1/workspaces",
        headers={"authorization": _bearer_for("owner-2")},
        json={"name": "Beta", "slug": f"beta-{uuid4().hex[:8]}"},
    )
    assert workspace_two.status_code == 201, workspace_two.text
    workspace_two_id = UUID(workspace_two.json()["id"])

    published = client.post(
        "/v1/marketplace/items",
        headers={"authorization": _bearer_for("owner-1")},
        json={
            "workspace_id": str(workspace_one_id),
            "name": "Private refund skill",
            "slug": f"private-refunds-{uuid4().hex[:8]}",
            "description": "Internal refund policy helper",
            "version": "1.0.0",
            "permissions": ["read-traces"],
            "reviewers": ["lead@example.com"],
        },
    )
    assert published.status_code == 201, published.text
    item_id = published.json()["id"]

    global_browse = client.get(
        "/v1/marketplace",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert global_browse.status_code == 200, global_browse.text
    global_ids = {
        item.get("id") or item.get("server_id")
        for item in global_browse.json()["items"]
    }
    assert item_id not in global_ids

    workspace_one_browse = client.get(
        f"/v1/marketplace?workspace_id={workspace_one_id}",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert workspace_one_browse.status_code == 200, workspace_one_browse.text
    workspace_one_ids = {
        item.get("id") or item.get("server_id")
        for item in workspace_one_browse.json()["items"]
    }
    assert item_id in workspace_one_ids

    workspace_two_browse = client.get(
        f"/v1/marketplace?workspace_id={workspace_two_id}",
        headers={"authorization": _bearer_for("owner-2")},
    )
    assert workspace_two_browse.status_code == 200, workspace_two_browse.text
    workspace_two_ids = {
        item.get("id") or item.get("server_id")
        for item in workspace_two_browse.json()["items"]
    }
    assert item_id not in workspace_two_ids

    cross_workspace_version = client.post(
        f"/v1/marketplace/items/{item_id}/versions",
        headers={"authorization": _bearer_for("owner-2")},
        json={
            "workspace_id": str(workspace_two_id),
            "version": "1.1.0",
            "changelog": "Attempted cross-workspace update.",
        },
    )
    assert cross_workspace_version.status_code == 404, cross_workspace_version.text

    cross_workspace_install = client.post(
        f"/v1/marketplace/items/{item_id}/install",
        headers={"authorization": _bearer_for("owner-2")},
        json={"workspace_id": str(workspace_two_id)},
    )
    assert cross_workspace_install.status_code == 404, cross_workspace_install.text


def test_marketplace_installs_are_admin_and_workspace_scoped(
    client: TestClient,
) -> None:
    workspace_one = client.post(
        "/v1/workspaces",
        headers={"authorization": _bearer_for("owner-1")},
        json={"name": "Acme", "slug": f"acme-{uuid4().hex[:8]}"},
    )
    assert workspace_one.status_code == 201, workspace_one.text
    workspace_one_id = UUID(workspace_one.json()["id"])

    workspace_two = client.post(
        "/v1/workspaces",
        headers={"authorization": _bearer_for("owner-2")},
        json={"name": "Beta", "slug": f"beta-{uuid4().hex[:8]}"},
    )
    assert workspace_two.status_code == 201, workspace_two.text
    workspace_two_id = UUID(workspace_two.json()["id"])

    member = client.post(
        f"/v1/workspaces/{workspace_one_id}/members",
        headers={"authorization": _bearer_for("owner-1")},
        json={"user_sub": "alice", "role": "member"},
    )
    assert member.status_code == 201, member.text

    member_install = client.post(
        "/v1/marketplace/items/first-party.salesforce/install",
        headers={"authorization": _bearer_for("alice")},
        json={"workspace_id": str(workspace_one_id)},
    )
    assert member_install.status_code == 403, member_install.text

    install_one = client.post(
        "/v1/marketplace/items/first-party.salesforce/install",
        headers={"authorization": _bearer_for("owner-1")},
        json={"workspace_id": str(workspace_one_id)},
    )
    assert install_one.status_code == 201, install_one.text

    install_two = client.post(
        "/v1/marketplace/items/first-party.salesforce/install",
        headers={"authorization": _bearer_for("owner-2")},
        json={"workspace_id": str(workspace_two_id)},
    )
    assert install_two.status_code == 201, install_two.text

    installs_one = client.get(
        f"/v1/marketplace/items/first-party.salesforce/installs?workspace_id={workspace_one_id}",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert installs_one.status_code == 200, installs_one.text
    assert [item["workspace_id"] for item in installs_one.json()["items"]] == [
        str(workspace_one_id)
    ]
