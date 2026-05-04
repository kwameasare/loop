"""Tests for the dp-runtime Prometheus middleware (P0.7b)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from loop_data_plane.metrics import (
    increment_turn_event,
    install_metrics,
)


def _make_app() -> FastAPI:
    app = FastAPI()
    install_metrics(app)

    @app.get("/healthz")
    def healthz() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/v1/turns/stream")
    def stream() -> dict[str, bool]:
        return {"ok": True}

    return app


def test_dp_metrics_endpoint_serves_prometheus_format() -> None:
    app = _make_app()
    with TestClient(app) as client:
        client.post("/v1/turns/stream", json={})
        body = client.get("/metrics").text
    assert "loop_data_plane_requests_total" in body
    assert "loop_data_plane_request_duration_seconds" in body
    assert "loop_data_plane_turn_events_total" in body


def test_dp_request_counter_labels_method_path_status() -> None:
    app = _make_app()
    with TestClient(app) as client:
        for _ in range(2):
            client.post("/v1/turns/stream", json={})
        body = client.get("/metrics").text
    assert (
        'loop_data_plane_requests_total{'
        'method="POST",path="/v1/turns/stream",status_class="2xx"} 2.0'
    ) in body


def test_dp_turn_event_counter_increments_per_kind() -> None:
    """The SSE streaming path calls increment_turn_event(kind) so
    dashboards can break down 200-OK-with-error-frame from
    200-OK-clean."""
    # Increment a few; the metric is module-level so we can call directly.
    increment_turn_event("token")
    increment_turn_event("token")
    increment_turn_event("complete")
    increment_turn_event("error")

    app = _make_app()
    with TestClient(app) as client:
        body = client.get("/metrics").text
    assert (
        'loop_data_plane_turn_events_total{event_kind="token"}' in body
    )
    assert (
        'loop_data_plane_turn_events_total{event_kind="complete"}' in body
    )
    assert (
        'loop_data_plane_turn_events_total{event_kind="error"}' in body
    )


def test_dp_install_metrics_is_idempotent() -> None:
    app = FastAPI()
    install_metrics(app)
    install_metrics(app)

    @app.get("/x")
    def x() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(app) as client:
        client.get("/x")
        body = client.get("/metrics").text
    assert (
        'loop_data_plane_requests_total{'
        'method="GET",path="/x",status_class="2xx"} 1.0'
    ) in body
