"""Tests for the cp-api Prometheus middleware (P0.7b).

We exercise the middleware via Starlette's TestClient against a tiny
inline FastAPI app. That keeps the test hermetic (no postgres, no
real cp routes) while still exercising the same code path the
production app uses.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from loop_control_plane.metrics import install_metrics


def _make_app() -> FastAPI:
    app = FastAPI()
    install_metrics(app)

    @app.get("/healthz")
    def healthz() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/v1/agents/{agent_id}")
    def agent(agent_id: str) -> dict[str, str]:
        return {"id": agent_id}

    @app.post("/v1/things")
    def thing() -> dict[str, str]:
        return {"ok": "yes"}

    @app.get("/v1/boom")
    def boom() -> None:
        raise RuntimeError("test-only")

    return app


def test_metrics_endpoint_serves_prometheus_format() -> None:
    app = _make_app()
    with TestClient(app) as client:
        # Make at least one request so a series exists.
        client.get("/v1/agents/abc")
        resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    assert "loop_control_plane_requests_total" in body
    assert "loop_control_plane_request_duration_seconds_bucket" in body
    # The standard Prometheus exposition format ships TYPE + HELP lines.
    assert "# HELP" in body
    assert "# TYPE" in body


def test_request_counter_increments_by_method_path_and_status_class() -> None:
    app = _make_app()
    # `raise_server_exceptions=False` so /v1/boom's RuntimeError lands
    # as a 500 response instead of propagating into the test runner.
    # The middleware still records the 5xx label.
    with TestClient(app, raise_server_exceptions=False) as client:
        for _ in range(3):
            client.get("/v1/agents/abc")
        client.post("/v1/things", json={})
        client.get("/v1/boom")
        body = client.get("/metrics").text

    # 3x 2xx GETs against /v1/agents/{agent_id}
    assert (
        'loop_control_plane_requests_total{'
        'method="GET",path="/v1/agents/{agent_id}",status_class="2xx"} 3.0'
    ) in body
    # 1x 2xx POST against /v1/things
    assert (
        'loop_control_plane_requests_total{'
        'method="POST",path="/v1/things",status_class="2xx"} 1.0'
    ) in body
    # 1x 5xx GET against /v1/boom
    assert (
        'loop_control_plane_requests_total{'
        'method="GET",path="/v1/boom",status_class="5xx"} 1.0'
    ) in body


def test_metrics_endpoint_skips_self() -> None:
    """/metrics requests must not show up in the request counter,
    otherwise scraping doubles each interval's count."""
    app = _make_app()
    with TestClient(app) as client:
        client.get("/v1/agents/abc")  # baseline
        # Scrape multiple times
        for _ in range(5):
            client.get("/metrics")
        body = client.get("/metrics").text
    # Only 1 GET to /v1/agents/{agent_id}; no /metrics counter
    assert (
        'loop_control_plane_requests_total{'
        'method="GET",path="/v1/agents/{agent_id}",status_class="2xx"} 1.0'
    ) in body
    assert "/metrics" not in [
        line.split('path="')[1].split('"')[0]
        for line in body.splitlines()
        if 'loop_control_plane_requests_total{' in line
    ]


def test_path_uses_route_template_not_literal_url() -> None:
    """Cardinality control: /v1/agents/abc and /v1/agents/xyz must
    bucket under /v1/agents/{agent_id} so we don't blow up Prometheus
    storage on workspace/agent ids."""
    app = _make_app()
    with TestClient(app) as client:
        client.get("/v1/agents/aaaa")
        client.get("/v1/agents/bbbb")
        client.get("/v1/agents/cccc")
        body = client.get("/metrics").text
    # Single bucket
    assert (
        'loop_control_plane_requests_total{'
        'method="GET",path="/v1/agents/{agent_id}",status_class="2xx"} 3.0'
    ) in body
    # No literal-id leakage
    assert "/v1/agents/aaaa" not in body
    assert "/v1/agents/cccc" not in body


def test_install_metrics_is_idempotent() -> None:
    """Calling install_metrics twice (e.g. via test reload) must not
    add a second middleware instance and double-count requests."""
    app = FastAPI()
    install_metrics(app)
    install_metrics(app)  # second call should be a no-op

    @app.get("/x")
    def x() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(app) as client:
        client.get("/x")
        body = client.get("/metrics").text
    # Exactly one increment, not two
    assert (
        'loop_control_plane_requests_total{'
        'method="GET",path="/x",status_class="2xx"} 1.0'
    ) in body
