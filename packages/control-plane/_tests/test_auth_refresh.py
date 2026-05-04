"""Tests for POST /v1/auth/refresh (P0.4).

Hermetic — uses cp's in-memory state + a hand-minted local-JWT for
the initial /v1/auth/exchange so the test exercises the full flow.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient
from loop_control_plane.app import create_app

_HS256_SECRET = "test-secret-please-rotate"
_PASETO_KEY = "k" * 32  # 32 bytes


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _make_id_token(sub: str = "user@example.com") -> str:
    """Mint an HS256 JWT cp's HS256Verifier accepts."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    claims = {
        "sub": sub,
        "iss": "https://loop.local/",
        "aud": "loop-cp",
        "iat": now,
        "exp": now + 3600,
    }
    h = _b64url(json.dumps(header, separators=(",", ":")).encode())
    c = _b64url(json.dumps(claims, separators=(",", ":")).encode())
    sig = hmac.new(
        _HS256_SECRET.encode(), f"{h}.{c}".encode(), hashlib.sha256
    ).digest()
    return f"{h}.{c}.{_b64url(sig)}"


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOOP_CP_LOCAL_JWT_SECRET", _HS256_SECRET)
    monkeypatch.setenv("LOOP_CP_PASETO_LOCAL_KEY", _PASETO_KEY)
    monkeypatch.setenv("LOOP_CP_AUTH_ISSUER", "https://loop.local/")
    monkeypatch.setenv("LOOP_CP_AUTH_AUDIENCE", "loop-cp")
    monkeypatch.setenv("LOOP_OTEL_ENDPOINT", "disabled")


@pytest.fixture
def client(env: None) -> TestClient:
    return TestClient(create_app())


def _initial_exchange(client: TestClient) -> tuple[str, str]:
    """Run the full /v1/auth/exchange flow and return (access, refresh)."""
    response = client.post("/v1/auth/exchange", json={"id_token": _make_id_token()})
    assert response.status_code == 200, response.text
    body = response.json()
    return body["access_token"], body["refresh_token"]


def test_refresh_returns_new_access_and_refresh_tokens(client: TestClient) -> None:
    _access, refresh = _initial_exchange(client)
    response = client.post("/v1/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "Bearer"
    assert body["access_expires_at_ms"] > body["refresh_expires_at_ms"] - 31 * 24 * 60 * 60 * 1000


def test_refresh_rotates_tokens(client: TestClient) -> None:
    """Successful refresh must mint a NEW refresh token; old one
    becomes invalid."""
    _, refresh = _initial_exchange(client)
    body = client.post("/v1/auth/refresh", json={"refresh_token": refresh}).json()
    assert body["refresh_token"] != refresh


def test_refresh_replays_are_rejected(client: TestClient) -> None:
    """The same refresh token used twice = compromise indicator. The
    second presentation must 401."""
    _, refresh = _initial_exchange(client)
    first = client.post("/v1/auth/refresh", json={"refresh_token": refresh})
    assert first.status_code == 200
    second = client.post("/v1/auth/refresh", json={"refresh_token": refresh})
    assert second.status_code == 401


def test_refresh_unknown_token_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/v1/auth/refresh",
        json={"refresh_token": "x" * 64},
    )
    assert response.status_code == 401


def test_refresh_rejects_short_token(client: TestClient) -> None:
    """Pydantic min_length guard."""
    response = client.post(
        "/v1/auth/refresh",
        json={"refresh_token": "short"},
    )
    assert response.status_code == 422


def test_refresh_chain_works_across_multiple_rotations(client: TestClient) -> None:
    """Sanity: a typical session refreshes many times. Each new
    refresh token must be redeemable in turn."""
    _, current_refresh = _initial_exchange(client)
    for _ in range(5):
        body = client.post(
            "/v1/auth/refresh", json={"refresh_token": current_refresh}
        ).json()
        current_refresh = body["refresh_token"]
        assert current_refresh
