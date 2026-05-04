"""Tests for workspace API-keys + secrets routes (P0.4 + P0.7a)."""

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
# API keys                                                                    #
# --------------------------------------------------------------------------- #


def test_create_api_key_returns_plaintext_once(
    client: TestClient, workspace_id: UUID
) -> None:
    response = client.post(
        f"/v1/workspaces/{workspace_id}/api-keys",
        headers={"authorization": _bearer_for("owner-1")},
        json={"name": "ci"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "ci"
    assert body["plaintext"].startswith("loop_sk_")
    assert "hash" not in body


def test_list_api_keys_omits_plaintext(
    client: TestClient, workspace_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    client.post(
        f"/v1/workspaces/{workspace_id}/api-keys",
        headers=headers,
        json={"name": "ci"},
    )
    response = client.get(f"/v1/workspaces/{workspace_id}/api-keys", headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert items
    assert all("plaintext" not in r and "hash" not in r for r in items)


def test_revoke_api_key_idempotent(client: TestClient, workspace_id: UUID) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    issued = client.post(
        f"/v1/workspaces/{workspace_id}/api-keys",
        headers=headers,
        json={"name": "ci"},
    ).json()
    key_id = issued["id"]
    first = client.delete(
        f"/v1/workspaces/{workspace_id}/api-keys/{key_id}", headers=headers
    )
    assert first.status_code == 200
    # Idempotent — service-side revoke handles already-revoked.
    second = client.delete(
        f"/v1/workspaces/{workspace_id}/api-keys/{key_id}", headers=headers
    )
    # Either 200 (idempotent succeed) or 404 (already gone). Both fine.
    assert second.status_code in (200, 404)


def test_api_key_routes_require_admin_for_writes(
    client: TestClient, workspace_id: UUID
) -> None:
    """Add a regular member; they can list but not create/revoke."""
    owner = {"authorization": _bearer_for("owner-1")}
    client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers=owner,
        json={"user_sub": "alice", "role": "member"},
    )
    alice = {"authorization": _bearer_for("alice")}

    list_resp = client.get(f"/v1/workspaces/{workspace_id}/api-keys", headers=alice)
    assert list_resp.status_code == 200

    create_resp = client.post(
        f"/v1/workspaces/{workspace_id}/api-keys",
        headers=alice,
        json={"name": "alice-key"},
    )
    assert create_resp.status_code in (401, 403)


def test_api_key_routes_emit_audit_events(
    client: TestClient, workspace_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    issued = client.post(
        f"/v1/workspaces/{workspace_id}/api-keys",
        headers=headers,
        json={"name": "ci"},
    ).json()
    client.delete(
        f"/v1/workspaces/{workspace_id}/api-keys/{issued['id']}", headers=headers
    )
    state = client.app.state.cp  # type: ignore[attr-defined]
    actions = [e.action for e in state.audit_events.list_for_workspace(workspace_id)]
    assert "workspace:api_key:create" in actions
    assert "workspace:api_key:revoke" in actions
    # AuditEvent stores `payload_hash`, never the raw payload — so the
    # plaintext is structurally inaccessible from the audit row. Verify
    # the rows do carry a hash so emission was complete.
    rows = list(state.audit_events.list_for_workspace(workspace_id))
    api_key_rows = [r for r in rows if r.action.startswith("workspace:api_key:")]
    assert all(r.payload_hash for r in api_key_rows)


# --------------------------------------------------------------------------- #
# Secrets                                                                     #
# --------------------------------------------------------------------------- #


def test_set_then_get_secret(client: TestClient, workspace_id: UUID) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    set_resp = client.put(
        f"/v1/workspaces/{workspace_id}/secrets/STRIPE_KEY",
        headers=headers,
        json={"value": "sk_live_secret_xyz"},
    )
    assert set_resp.status_code == 200, set_resp.text
    assert set_resp.json()["version"] == 1
    get_resp = client.get(
        f"/v1/workspaces/{workspace_id}/secrets/STRIPE_KEY", headers=headers
    )
    assert get_resp.status_code == 200
    assert get_resp.json() == {"name": "STRIPE_KEY", "value": "sk_live_secret_xyz"}


def test_set_secret_requires_admin(client: TestClient, workspace_id: UUID) -> None:
    owner = {"authorization": _bearer_for("owner-1")}
    client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers=owner,
        json={"user_sub": "alice", "role": "member"},
    )
    alice = {"authorization": _bearer_for("alice")}
    response = client.put(
        f"/v1/workspaces/{workspace_id}/secrets/STRIPE_KEY",
        headers=alice,
        json={"value": "evil"},
    )
    assert response.status_code in (401, 403)


def test_get_secret_works_for_any_member(
    client: TestClient, workspace_id: UUID
) -> None:
    """Members read secrets so the agent runtime (acting as the
    service principal embedded as a workspace member) can access
    workspace-scoped credentials."""
    owner = {"authorization": _bearer_for("owner-1")}
    client.put(
        f"/v1/workspaces/{workspace_id}/secrets/SHARED",
        headers=owner,
        json={"value": "value-1"},
    )
    client.post(
        f"/v1/workspaces/{workspace_id}/members",
        headers=owner,
        json={"user_sub": "alice", "role": "member"},
    )
    alice = {"authorization": _bearer_for("alice")}
    response = client.get(
        f"/v1/workspaces/{workspace_id}/secrets/SHARED", headers=alice
    )
    assert response.status_code == 200


def test_rotate_secret_bumps_version(client: TestClient, workspace_id: UUID) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    client.put(
        f"/v1/workspaces/{workspace_id}/secrets/X",
        headers=headers,
        json={"value": "v1"},
    )
    rotate_resp = client.post(
        f"/v1/workspaces/{workspace_id}/secrets/X/rotate",
        headers=headers,
        json={"new_value": "v2"},
    )
    assert rotate_resp.status_code == 200, rotate_resp.text
    assert rotate_resp.json()["version"] == 2
    # GET now returns the new value.
    get_resp = client.get(
        f"/v1/workspaces/{workspace_id}/secrets/X", headers=headers
    )
    assert get_resp.json()["value"] == "v2"


def test_delete_secret_returns_204(client: TestClient, workspace_id: UUID) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    client.put(
        f"/v1/workspaces/{workspace_id}/secrets/X",
        headers=headers,
        json={"value": "v1"},
    )
    response = client.delete(
        f"/v1/workspaces/{workspace_id}/secrets/X", headers=headers
    )
    assert response.status_code == 204
    # Subsequent GET returns 404
    response = client.get(
        f"/v1/workspaces/{workspace_id}/secrets/X", headers=headers
    )
    assert response.status_code == 404


def test_get_unknown_secret_returns_404(
    client: TestClient, workspace_id: UUID
) -> None:
    response = client.get(
        f"/v1/workspaces/{workspace_id}/secrets/NEVER_SET",
        headers={"authorization": _bearer_for("owner-1")},
    )
    assert response.status_code == 404


def test_secret_namespace_isolates_workspaces(client: TestClient) -> None:
    """Two workspaces using the same secret name must not collide."""
    headers = {"authorization": _bearer_for("owner-1")}
    a_id = UUID(
        client.post(
            "/v1/workspaces", headers=headers, json={"name": "A", "slug": "a"}
        ).json()["id"]
    )
    b_id = UUID(
        client.post(
            "/v1/workspaces", headers=headers, json={"name": "B", "slug": "b"}
        ).json()["id"]
    )
    client.put(
        f"/v1/workspaces/{a_id}/secrets/STRIPE_KEY",
        headers=headers,
        json={"value": "a-value"},
    )
    client.put(
        f"/v1/workspaces/{b_id}/secrets/STRIPE_KEY",
        headers=headers,
        json={"value": "b-value"},
    )
    a_get = client.get(
        f"/v1/workspaces/{a_id}/secrets/STRIPE_KEY", headers=headers
    ).json()
    b_get = client.get(
        f"/v1/workspaces/{b_id}/secrets/STRIPE_KEY", headers=headers
    ).json()
    assert a_get["value"] == "a-value"
    assert b_get["value"] == "b-value"


def test_secret_routes_emit_audit_events(
    client: TestClient, workspace_id: UUID
) -> None:
    """All four secret operations write audit rows (set/get/rotate/delete)."""
    headers = {"authorization": _bearer_for("owner-1")}
    client.put(
        f"/v1/workspaces/{workspace_id}/secrets/X",
        headers=headers,
        json={"value": "v1"},
    )
    client.get(f"/v1/workspaces/{workspace_id}/secrets/X", headers=headers)
    client.post(
        f"/v1/workspaces/{workspace_id}/secrets/X/rotate",
        headers=headers,
        json={"new_value": "v2"},
    )
    client.delete(f"/v1/workspaces/{workspace_id}/secrets/X", headers=headers)
    state = client.app.state.cp  # type: ignore[attr-defined]
    actions = [e.action for e in state.audit_events.list_for_workspace(workspace_id)]
    assert "workspace:secret:set" in actions
    assert "workspace:secret:get" in actions
    assert "workspace:secret:rotate" in actions
    assert "workspace:secret:delete" in actions


def test_secret_audit_payload_hash_excludes_plaintext_by_design(
    client: TestClient, workspace_id: UUID
) -> None:
    """`AuditEvent` schema stores `payload_hash` only — the raw
    payload is structurally inaccessible from the audit row, so the
    plaintext can NEVER be recovered from the audit log even if a
    future caller forgot the redaction discipline. This test pins
    that invariant."""
    headers = {"authorization": _bearer_for("owner-1")}
    client.put(
        f"/v1/workspaces/{workspace_id}/secrets/X",
        headers=headers,
        json={"value": "ultra-secret-do-not-log"},
    )
    state = client.app.state.cp  # type: ignore[attr-defined]
    rows = list(state.audit_events.list_for_workspace(workspace_id))
    assert all(not hasattr(r, "payload") for r in rows)
    # Payload-hash existence proves the row was written with
    # the right shape.
    secret_rows = [r for r in rows if r.action.startswith("workspace:secret:")]
    assert secret_rows
    assert all(r.payload_hash for r in secret_rows)
