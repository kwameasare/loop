"""Tests for the marketplace browse route."""

from __future__ import annotations

from datetime import UTC, datetime

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
