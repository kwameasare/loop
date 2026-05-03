"""Httpx control-plane transport tests for S903 — cassette + live mock.

These tests prove that the CLI's request/stream contract is wired
through real httpx (not OfflineTransport / FakeTransport). The
``LOOP_CLI_LIVE_TESTS=1`` env var promotes the smoke-test to dial a
local cp-api uvicorn run; without it, all assertions run against
httpx.MockTransport with cassette-recorded responses.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
import yaml

from loop.cli import (
    ControlPlaneTransportError,
    HttpxControlPlaneTransport,
    main,
)

CASSETTES = Path(__file__).parent / "cassettes" / "cli"


def _cassette(name: str) -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load((CASSETTES / name).read_text()))


def _mock_client(seen: list[httpx.Request], cassettes: dict[str, dict[str, Any]]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        key = f"{request.method} {request.url.path}"
        if key not in cassettes:
            return httpx.Response(404, text=f"no cassette for {key}")
        cassette = cassettes[key]
        return httpx.Response(
            int(cassette["status_code"]),
            headers=cast(dict[str, str], cassette.get("headers", {})),
            text=str(cassette["body"]),
        )

    return httpx.Client(transport=httpx.MockTransport(handler), base_url="http://cp.test")


def test_httpx_transport_request_serialises_json_and_attaches_bearer() -> None:
    cassette = _cassette("workspaces_create.yaml")
    seen: list[httpx.Request] = []
    cassettes = {"POST /v1/workspaces": cassette["response"]}
    with _mock_client(seen, cassettes) as client:
        transport = HttpxControlPlaneTransport("http://cp.test", client=client)
        result = transport.request(
            "POST",
            "/v1/workspaces",
            json_body={"name": "acme"},
            token="token-abc",  # noqa: S106 — fixture token
        )

    assert result["id"] == "ws_42"
    assert result["name"] == "acme"
    assert seen[0].headers["authorization"] == "Bearer token-abc"
    assert seen[0].headers["accept"] == "application/json"
    assert json.loads(seen[0].content) == {"name": "acme"}


def test_httpx_transport_raises_on_4xx_with_status_and_body() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(401, json={"error": "unauthorised"})

    client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="http://cp.test"
    )
    with HttpxControlPlaneTransport("http://cp.test", client=client) as transport:
        with pytest.raises(ControlPlaneTransportError) as exc:
            transport.request("GET", "/v1/workspaces", token="bad")
        assert exc.value.status_code == 401
        assert exc.value.method == "GET"
        assert "unauthorised" in exc.value.body


def test_httpx_transport_stream_yields_each_log_line() -> None:
    seen: list[httpx.Request] = []
    body = "line one\nline two\nline three\n"

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            text=body,
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="http://cp.test"
    )
    with HttpxControlPlaneTransport("http://cp.test", client=client) as transport:
        lines = list(transport.stream("/logs/agent_42", token="t"))

    assert lines == ["line one", "line two", "line three"]
    assert seen[0].headers["authorization"] == "Bearer t"


def test_httpx_transport_stream_raises_on_4xx() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="forbidden")

    client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="http://cp.test"
    )
    with HttpxControlPlaneTransport("http://cp.test", client=client) as transport:
        with pytest.raises(ControlPlaneTransportError) as exc:
            list(transport.stream("/logs/x"))
        assert exc.value.status_code == 403


def test_cli_login_through_httpx_transport_persists_credentials(tmp_path: Path) -> None:
    """End-to-end smoke: ``loop login`` uses HttpxControlPlaneTransport
    against a mocked cp-api and writes credentials to disk."""

    seen: list[httpx.Request] = []
    cassettes = {
        "POST /auth/device-code": {
            "status_code": 200,
            "body": json.dumps(
                {
                    "verification_url": "https://loop.test/device",
                    "user_code": "ABCD-EFGH",
                    "device_code": "dev_xyz",
                }
            ),
        },
        "POST /auth/device-token": {
            "status_code": 200,
            "body": json.dumps(
                {
                    "access_token": "real-access",
                    "refresh_token": "real-refresh",
                    "workspace_id": "ws_42",
                    "expires_at": 1_900_000_000,
                }
            ),
        },
    }
    client = _mock_client(seen, cassettes)
    transport = HttpxControlPlaneTransport("http://cp.test", client=client)
    out = io.StringIO()

    code = main(["login"], transport=transport, home=tmp_path, out=out)

    creds_path = tmp_path / ".loop" / "credentials"
    assert code == 0
    assert "https://loop.test/device" in out.getvalue()
    assert creds_path.read_text().count("real-access") == 1
    assert seen[0].url.path == "/auth/device-code"
    assert seen[1].url.path == "/auth/device-token"
    assert json.loads(seen[1].content) == {"device_code": "dev_xyz"}


def test_default_transport_picks_httpx_when_env_set(monkeypatch: pytest.MonkeyPatch) -> None:
    from loop.cli import default_transport

    monkeypatch.setenv("LOOP_CP_API_URL", "http://cp.test")
    transport = default_transport()
    assert isinstance(transport, HttpxControlPlaneTransport)


def test_default_transport_falls_back_to_offline_when_env_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from loop.cli import OfflineTransport, default_transport

    monkeypatch.delenv("LOOP_CP_API_URL", raising=False)
    transport = default_transport()
    assert isinstance(transport, OfflineTransport)
