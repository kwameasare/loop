"""OpenAI-compatible SSE fixture for runtime performance workflows.

This is not a Loop service. The S913 runtime benchmark runs the real
`dp-runtime` image, which then calls this fixture through the same
httpx/OpenAI provider path used for live traffic.
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class OpenAISseFixture(BaseHTTPRequestHandler):
    server_version = "loop-openai-sse-fixture/0.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._json({"ok": True})
            return
        self.send_error(404, "not found")

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", "0") or "0")
        self.rfile.read(length)
        if self.path != "/v1/chat/completions":
            self.send_error(404, "not found")
            return
        data = (
            b'data: {"choices":[{"delta":{"content":"perf"}}]}\n'
            b'data: {"choices":[{"delta":{"content":" ok"}}]}\n'
            b'data: {"usage":{"prompt_tokens":12,"completion_tokens":2}}\n'
            b"data: [DONE]\n"
        )
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, payload: dict[str, object]) -> None:
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def make_server(port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("0.0.0.0", port), OpenAISseFixture)  # noqa: S104


def main() -> None:
    port = int(os.environ.get("LOOP_OPENAI_FIXTURE_PORT", "8089"))
    make_server(port).serve_forever()


if __name__ == "__main__":
    main()
