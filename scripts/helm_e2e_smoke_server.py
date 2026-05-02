"""Tiny HTTP server used by the Helm kind smoke workflow.

The workflow builds this into a local image and points every Loop chart
component at it. That lets CI validate Helm wiring, readiness, Services, and
the turn request path without requiring production images or real LLM keys.
"""

from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread


class SmokeHandler(BaseHTTPRequestHandler):
    server_version = "loop-helm-smoke/0.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._send_json({"ok": True})
            return
        self.send_error(404, "not found")

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", "0") or "0")
        body = self.rfile.read(length).decode("utf-8") if length else ""
        if self.path == "/v1/turns/stream" or "text/event-stream" in self.headers.get("accept", ""):
            self._send_sse(
                (
                    ("delta", {"text": "helm-e2e"}),
                    ("delta", {"text": "-ok"}),
                    ("done", {"turn_id": "helm-e2e-smoke", "received": body}),
                )
            )
            return
        self._send_json(
            {
                "turn_id": "helm-e2e-smoke",
                "reply": {"text": "helm-e2e-ok"},
                "received": body,
            }
        )

    def _send_json(self, payload: dict[str, object], status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_sse(self, events: tuple[tuple[str, dict[str, object]], ...]) -> None:
        frames: list[str] = []
        for event, payload in events:
            frames.append(f"event: {event}\ndata: {json.dumps(payload)}\n\n")
        data = "".join(frames).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.send_header("cache-control", "no-cache")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def make_server(port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("0.0.0.0", port), SmokeHandler)  # noqa: S104


def _ports() -> list[int]:
    raw = os.environ.get("HELM_SMOKE_PORTS", "8080,8081,8082,8003")
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


def main() -> None:
    servers = [make_server(port) for port in _ports()]
    for server in servers:
        Thread(target=server.serve_forever, daemon=True).start()
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
