from __future__ import annotations

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar, cast

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "e2e_web_smoke.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "e2e-web-smoke.yml"


class DemoHandler(BaseHTTPRequestHandler):
    answer = "Loop is an open-source agent runtime for support teams."
    requests: ClassVar[list[dict[str, Any]]] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", "0"))
        body = json.loads(self.rfile.read(length))
        type(self).requests.append(body)
        payload = json.dumps({"answer": self.answer}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


def _run_server(
    answer: str,
) -> tuple[ThreadingHTTPServer, type[DemoHandler], str]:
    class Handler(DemoHandler):
        pass

    Handler.answer = answer
    Handler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = cast(tuple[str, int], server.server_address[:2])
    return server, Handler, f"http://{host}:{port}"


def test_e2e_web_smoke_asserts_demo_answer() -> None:
    server, handler, url = _run_server("Loop is an open-source agent runtime.")
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--url",
                url,
                "--question",
                "What is Loop?",
                "--expected-answer",
                "open-source agent runtime",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    finally:
        server.shutdown()

    assert result.returncode == 0, result.stderr
    assert "e2e_web_smoke: OK" in result.stdout
    assert handler.requests == [{"message": "What is Loop?"}]


def test_e2e_web_smoke_fails_on_wrong_answer() -> None:
    server, _handler, url = _run_server("I cannot answer that.")
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--url",
                url,
                "--expected-answer",
                "open-source agent runtime",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    finally:
        server.shutdown()

    assert result.returncode == 1
    assert "answer mismatch" in result.stderr


def test_e2e_web_smoke_runs_nightly_in_ci() -> None:
    workflow = cast(dict[object, Any], yaml.safe_load(WORKFLOW.read_text()))
    assert "schedule" in workflow[True]
    jobs = cast(dict[str, Any], workflow["jobs"])
    job = jobs["e2e-web-smoke"]
    assert job["env"]["LOOP_DEMO_URL"] == "${{ vars.LOOP_DEMO_URL }}"
    assert any(step.get("run") == "bash scripts/e2e_web_smoke.sh" for step in job["steps"])
