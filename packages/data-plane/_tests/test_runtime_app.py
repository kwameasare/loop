"""HTTP integration coverage for the S902 dp-runtime ASGI app."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any, cast

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]
WORKSPACE_ID = "11111111-1111-4111-8111-111111111111"
CONVERSATION_ID = "22222222-2222-4222-8222-222222222222"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _OpenAIFixture(BaseHTTPRequestHandler):
    server_version = "loop-s902-openai-fixture/0.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", "0") or "0")
        body = self.rfile.read(length).decode("utf-8")
        cast(Any, self.server).seen.append(
            {"path": self.path, "headers": dict(self.headers), "body": body}
        )
        data = (
            b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n'
            b'data: {"choices":[{"delta":{"content":" Loop"}}]}\n'
            b'data: {"usage":{"prompt_tokens":10,"completion_tokens":2}}\n'
            b"data: [DONE]\n"
        )
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


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
    raise AssertionError(f"dp-runtime did not become ready: {last_error}")


@pytest.fixture
def runtime_server() -> Iterator[tuple[str, list[dict[str, Any]]]]:
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv executable is required for S902 integration test")

    provider = ThreadingHTTPServer(("127.0.0.1", 0), _OpenAIFixture)
    provider.seen = []  # type: ignore[attr-defined]
    provider_thread = Thread(target=provider.serve_forever, daemon=True)
    provider_thread.start()

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.update(
        {
            "LOOP_DP_BUILD_TIME": "2026-05-03T18:50:00Z",
            "LOOP_DP_COMMIT_SHA": "7654321",
            "LOOP_DP_DEFAULT_MODEL": "gpt-4o-mini",
            "LOOP_DP_OPENAI_BASE_URL": f"http://127.0.0.1:{provider.server_address[1]}",
            "LOOP_DP_VERSION": "0.1.0-test",
            "LOOP_GATEWAY_OPENAI_API_KEY": "s902-test-key",
        }
    )
    proc = subprocess.Popen(
        [
            uv,
            "run",
            "uvicorn",
            "loop_data_plane.runtime_app:app",
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
        yield base_url, cast(list[dict[str, Any]], provider.seen)  # type: ignore[attr-defined]
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        provider.shutdown()
        provider.server_close()


def _turn_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "workspace_id": WORKSPACE_ID,
        "conversation_id": CONVERSATION_ID,
        "user_id": "user-s902",
        "channel": "web",
        "input": "Say hello through the real runtime",
        "request_id": "s902-turn-1",
    }
    body.update(overrides)
    return body


def _frame_payloads(body: str) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for block in body.strip().split("\n\n"):
        lines = block.splitlines()
        data = next(line.removeprefix("data: ") for line in lines if line.startswith("data: "))
        payloads.append(cast(dict[str, Any], json.loads(data)))
    return payloads


def test_uvicorn_runtime_streams_turn_events_through_turn_executor(
    runtime_server: tuple[str, list[dict[str, Any]]],
) -> None:
    base_url, provider_seen = runtime_server
    with httpx.Client(base_url=base_url, timeout=5) as client:
        response = client.post(
            "/v1/turns",
            headers={"accept": "text/event-stream"},
            json=_turn_body(),
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "event: turn_event" in response.text
    assert "event: done" in response.text
    payloads = _frame_payloads(response.text)
    assert [p["payload"]["text"] for p in payloads if p.get("type") == "token"] == [
        "Hello",
        " Loop",
    ]
    assert payloads[-1] == {"turn_id": "s902-turn-1"}
    assert provider_seen[0]["path"] == "/v1/chat/completions"
    headers = {k.lower(): v for k, v in provider_seen[0]["headers"].items()}
    assert headers["authorization"] == "Bearer s902-test-key"
    assert json.loads(provider_seen[0]["body"])["stream"] is True


def test_runtime_turn_rejects_empty_turn(
    runtime_server: tuple[str, list[dict[str, Any]]],
) -> None:
    base_url, _provider_seen = runtime_server
    with httpx.Client(base_url=base_url, timeout=5) as client:
        response = client.post("/v1/turns", json=_turn_body(input=None))

    assert response.status_code == 422
    assert "either content or input is required" in response.text
