"""HTTP integration coverage for the S901 cp-api ASGI app."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from loop_control_plane.auth import HS256Verifier

ROOT = Path(__file__).resolve().parents[3]
ISSUER = "https://test.auth0.loop.example/"
AUDIENCE = "https://api.loop.test"
JWT_SECRET = "s901-local-jwt-secret"  # noqa: S105
PASETO_KEY = "s901-local-paseto-key-32-bytes!!"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _id_token() -> str:
    now = int(time.time())
    verifier = HS256Verifier(secret=JWT_SECRET, issuer=ISSUER, audience=AUDIENCE)
    return verifier.sign(
        {
            "sub": "auth0|s901-user",
            "iss": ISSUER,
            "aud": AUDIENCE,
            "exp": now + 300,
            "iat": now,
            "email": "s901@example.com",
        }
    )


def _wait_until_ready(base_url: str, proc: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + 20
    last_error = ""
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            stderr = proc.stderr.read().decode() if proc.stderr else ""
            raise AssertionError(f"uvicorn exited early: {stderr}")
        try:
            response = httpx.get(f"{base_url}/healthz", timeout=1)
            if response.status_code == 200:
                return
            last_error = response.text
        except httpx.HTTPError as exc:
            last_error = str(exc)
        time.sleep(0.2)
    raise AssertionError(f"cp-api did not become ready: {last_error}")


@pytest.fixture
def cp_api_server() -> Iterator[str]:
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv executable is required for S901 cp-api integration test")

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.update(
        {
            "LOOP_CP_AUTH_AUDIENCE": AUDIENCE,
            "LOOP_CP_AUTH_ISSUER": ISSUER,
            "LOOP_CP_BUILD_TIME": "2026-05-03T18:30:00Z",
            "LOOP_CP_COMMIT_SHA": "1234567",
            "LOOP_CP_LOCAL_JWT_SECRET": JWT_SECRET,
            "LOOP_CP_PASETO_LOCAL_KEY": PASETO_KEY,
            "LOOP_CP_VERSION": "0.1.0-test",
        }
    )
    proc = subprocess.Popen(
        [
            uv,
            "run",
            "uvicorn",
            "loop_control_plane.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_until_ready(base_url, proc)
        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def _json(response: httpx.Response) -> dict[str, Any]:
    data = response.json()
    assert isinstance(data, dict)
    return cast(dict[str, Any], data)


def test_uvicorn_cp_api_serves_health_auth_workspaces_agents_and_audit(
    cp_api_server: str,
) -> None:
    with httpx.Client(base_url=cp_api_server, timeout=5) as client:
        health = _json(client.get("/healthz"))
        assert health["ok"] is True
        assert health["status"] == "healthy"

        exchange = _json(client.post("/v1/auth/exchange", json={"id_token": _id_token()}))
        token = exchange["access_token"]
        headers = {"Authorization": f"Bearer {token}", "X-Request-Id": "s901-req"}

        missing_auth = client.get("/v1/workspaces")
        assert missing_auth.status_code == 401
        assert _json(missing_auth)["code"] == "LOOP-API-101"

        created = _json(
            client.post(
                "/v1/workspaces",
                headers=headers,
                json={"name": "S901 Workspace", "slug": "s901-workspace"},
            )
        )
        workspace_id = created["id"]

        listed = _json(client.get("/v1/workspaces", headers=headers))
        assert listed["total"] == 1
        assert listed["items"][0]["slug"] == "s901-workspace"

        fetched = _json(client.get(f"/v1/workspaces/{workspace_id}", headers=headers))
        assert fetched["id"] == workspace_id

        patched = _json(
            client.patch(
                f"/v1/workspaces/{workspace_id}",
                headers=headers,
                json={"name": "S901 Renamed"},
            )
        )
        assert patched["name"] == "S901 Renamed"

        agent_headers = {**headers, "X-Loop-Workspace-Id": workspace_id}
        agent = _json(
            client.post(
                "/v1/agents",
                headers=agent_headers,
                json={"name": "Support Agent", "slug": "support-agent"},
            )
        )
        agent_id = agent["id"]

        agents = _json(client.get("/v1/agents", headers=agent_headers))
        assert agents["items"][0]["id"] == agent_id

        fetched_agent = _json(client.get(f"/v1/agents/{agent_id}", headers=agent_headers))
        assert fetched_agent["slug"] == "support-agent"

        audit = _json(
            client.get(
                "/v1/audit/events",
                headers=headers,
                params={"workspace_id": workspace_id},
            )
        )
        actions = {item["action"] for item in audit["items"]}
        assert {"workspace:create", "workspace:update", "agent:create"} <= actions
