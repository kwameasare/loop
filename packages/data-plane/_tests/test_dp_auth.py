"""Tests for dp-runtime authentication (P0.1).

Hermetic — uses TestClient against an inline dp app that swaps the
real `TurnExecutor` for a stub so we don't make LLM calls during
auth tests.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient
from loop_control_plane.paseto import encode_local
from loop_data_plane._auth import (
    DpAuthError,
    enforce_workspace_match,
)

# 32-byte test PASETO key. cp + dp share this in production.
_TEST_KEY = b"k" * 32


@pytest.fixture
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the PASETO key + disable OTLP for tests."""
    monkeypatch.setenv("LOOP_CP_PASETO_LOCAL_KEY", _TEST_KEY.decode())
    monkeypatch.setenv("LOOP_OTEL_ENDPOINT", "disabled")
    monkeypatch.delenv("LOOP_DP_AUTH_DISABLE", raising=False)


def _bearer_for(sub: str, *, workspaces: list[str] | None = None) -> str:
    now_ms = int(time.time() * 1000)
    claims: dict[str, object] = {"sub": sub}
    if workspaces is not None:
        claims["workspaces"] = workspaces
    token = encode_local(
        claims=claims, key=_TEST_KEY, now_ms=now_ms, expires_in_ms=3600 * 1000
    )
    return f"Bearer {token}"


# --------------------------------------------------------------------------- #
# enforce_workspace_match — pure-function tests                              #
# --------------------------------------------------------------------------- #


def test_enforce_match_accepts_when_sub_matches_user_id() -> None:
    enforce_workspace_match(
        claims={"sub": "user-1"},
        body_workspace_id="ws-1",
        body_user_id="user-1",
    )


def test_enforce_match_rejects_sub_mismatch() -> None:
    """An authenticated user X must not pose as user Y."""
    with pytest.raises(DpAuthError):
        enforce_workspace_match(
            claims={"sub": "user-1"},
            body_workspace_id="ws-1",
            body_user_id="user-2",
        )


def test_enforce_match_accepts_workspace_in_allowlist() -> None:
    enforce_workspace_match(
        claims={"sub": "user-1", "workspaces": ["ws-1", "ws-2"]},
        body_workspace_id="ws-1",
        body_user_id="user-1",
    )


def test_enforce_match_rejects_workspace_not_in_allowlist() -> None:
    """User authenticates and IS user-1, but body claims workspace
    they're not a member of."""
    with pytest.raises(DpAuthError):
        enforce_workspace_match(
            claims={"sub": "user-1", "workspaces": ["ws-1"]},
            body_workspace_id="ws-9",
            body_user_id="user-1",
        )


def test_enforce_match_rejects_missing_sub_claim() -> None:
    with pytest.raises(DpAuthError):
        enforce_workspace_match(
            claims={"workspaces": ["ws-1"]},
            body_workspace_id="ws-1",
            body_user_id="user-1",
        )


def test_enforce_match_skips_when_auth_disabled() -> None:
    """The dev bypass path: if the dependency saw
    LOOP_DP_AUTH_DISABLE, the synthetic claims include
    `_dp_auth_disabled` and we skip the cross-check too."""
    enforce_workspace_match(
        claims={"sub": "anyone", "_dp_auth_disabled": True},
        body_workspace_id="ws-1",
        body_user_id="user-anyone",
    )


# --------------------------------------------------------------------------- #
# Route-level dependency — full /v1/turns flow                               #
# --------------------------------------------------------------------------- #


def _build_app_with_stub_executor() -> tuple[TestClient, list[dict[str, object]]]:
    """Build a minimal dp app with a dict body type + the real auth
    dependency so we test the auth path without LLM calls."""
    from fastapi import Body, FastAPI
    from loop_data_plane._auth import AUTH_CALLER, enforce_workspace_match

    app = FastAPI()
    seen: list[dict[str, object]] = []

    @app.post("/v1/turns/stream", response_model=None)
    async def post_turn_stream(
        body: dict[str, object] = Body(...),
        claims: dict[str, object] = AUTH_CALLER,
    ) -> dict[str, object]:
        enforce_workspace_match(
            claims=claims,
            body_workspace_id=str(body["workspace_id"]),
            body_user_id=str(body["user_id"]),
        )
        seen.append({"sub": claims.get("sub"), "ws": str(body["workspace_id"])})
        return {"ok": True}

    return TestClient(app), seen


def _valid_body() -> dict[str, object]:
    return {
        "workspace_id": "00000000-0000-0000-0000-000000000001",
        "conversation_id": "00000000-0000-0000-0000-000000000002",
        "user_id": "user-1",
        "input": "say hi",
    }


def test_dp_rejects_request_with_no_authorization_header(auth_env: None) -> None:
    client, _ = _build_app_with_stub_executor()
    response = client.post("/v1/turns/stream", json=_valid_body())
    assert response.status_code == 401


def test_dp_rejects_request_with_malformed_bearer(auth_env: None) -> None:
    client, _ = _build_app_with_stub_executor()
    response = client.post(
        "/v1/turns/stream",
        headers={"authorization": "NotBearer xxx"},
        json=_valid_body(),
    )
    assert response.status_code == 401


def test_dp_rejects_request_with_bogus_token_signature(auth_env: None) -> None:
    """A token signed with the wrong key must be rejected."""
    bad_token = encode_local(
        claims={"sub": "user-1"},
        key=b"y" * 32,  # different key
        now_ms=int(time.time() * 1000),
        expires_in_ms=3600 * 1000,
    )
    client, _ = _build_app_with_stub_executor()
    response = client.post(
        "/v1/turns/stream",
        headers={"authorization": f"Bearer {bad_token}"},
        json=_valid_body(),
    )
    assert response.status_code == 401


def test_dp_accepts_request_with_valid_bearer_and_matching_user(auth_env: None) -> None:
    client, seen = _build_app_with_stub_executor()
    response = client.post(
        "/v1/turns/stream",
        headers={"authorization": _bearer_for("user-1")},
        json=_valid_body(),
    )
    assert response.status_code == 200, response.text
    assert seen == [
        {"sub": "user-1", "ws": "00000000-0000-0000-0000-000000000001"}
    ]


def test_dp_rejects_when_token_sub_does_not_match_body_user_id(auth_env: None) -> None:
    """Closes the open-relay vector: authenticated user-X must not
    submit a turn claiming to be user-Y."""
    client, _ = _build_app_with_stub_executor()
    response = client.post(
        "/v1/turns/stream",
        headers={"authorization": _bearer_for("user-X")},
        json=_valid_body(),  # body says user_id=user-1
    )
    assert response.status_code == 401


def test_dp_rejects_when_workspace_not_in_allowlist_claim(auth_env: None) -> None:
    """When token includes `workspaces` claim, body.workspace_id must
    be a member."""
    client, _ = _build_app_with_stub_executor()
    response = client.post(
        "/v1/turns/stream",
        headers={
            "authorization": _bearer_for(
                "user-1", workspaces=["00000000-0000-0000-0000-aaaaaaaaaaaa"]
            )
        },
        json=_valid_body(),
    )
    assert response.status_code == 401


def test_dp_accepts_when_workspace_is_in_allowlist_claim(auth_env: None) -> None:
    client, _ = _build_app_with_stub_executor()
    response = client.post(
        "/v1/turns/stream",
        headers={
            "authorization": _bearer_for(
                "user-1",
                workspaces=["00000000-0000-0000-0000-000000000001", "other-ws"],
            )
        },
        json=_valid_body(),
    )
    assert response.status_code == 200


def test_dp_disable_env_bypasses_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """The dev path: LOOP_DP_AUTH_DISABLE=1 lets unauthenticated
    requests through. Ensures the existing test fixtures (which
    still use the bypass) keep working."""
    monkeypatch.setenv("LOOP_DP_AUTH_DISABLE", "1")
    monkeypatch.setenv("LOOP_OTEL_ENDPOINT", "disabled")
    client, _ = _build_app_with_stub_executor()
    response = client.post("/v1/turns/stream", json=_valid_body())
    assert response.status_code == 200


def test_dp_missing_paseto_key_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """When neither the key nor the disable flag is set, requests
    fail with a clear server-misconfiguration message rather than
    silently allowing or 500-ing on import."""
    monkeypatch.delenv("LOOP_CP_PASETO_LOCAL_KEY", raising=False)
    monkeypatch.delenv("LOOP_DP_AUTH_DISABLE", raising=False)
    monkeypatch.setenv("LOOP_OTEL_ENDPOINT", "disabled")
    client, _ = _build_app_with_stub_executor()
    response = client.post(
        "/v1/turns/stream",
        headers={"authorization": "Bearer anything"},
        json=_valid_body(),
    )
    assert response.status_code == 401
