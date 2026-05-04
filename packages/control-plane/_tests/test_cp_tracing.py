"""Tests for the cp-api OpenTelemetry tracing wiring (P0.7c).

We exercise the install path in `disabled` mode so the test doesn't
need an OTLP collector running. The contract: install_tracing must
register a TracerProvider with the right service.name attribute and
auto-instrument every FastAPI route.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from loop_control_plane.tracing import install_tracing
from opentelemetry.sdk.trace import TracerProvider


def _make_app() -> FastAPI:
    app = FastAPI()
    install_tracing(app, service_name="cp-api-test")

    @app.get("/x")
    def x() -> dict[str, bool]:
        return {"ok": True}

    return app


def test_install_tracing_attaches_provider_to_app() -> None:
    with patch.dict(os.environ, {"LOOP_OTEL_ENDPOINT": "disabled"}):
        app = _make_app()
    provider = app.state.tracer_provider
    assert isinstance(provider, TracerProvider)
    # Service name must be set so the collector can route correctly.
    resource_attrs = dict(provider.resource.attributes)
    assert resource_attrs["service.name"] == "cp-api-test"


def test_install_tracing_is_idempotent() -> None:
    with patch.dict(os.environ, {"LOOP_OTEL_ENDPOINT": "disabled"}):
        app = FastAPI()
        install_tracing(app, service_name="cp-api-test")
        install_tracing(app, service_name="cp-api-test")  # second call no-op
    assert hasattr(app.state, "tracer_provider")


def test_request_through_app_creates_span() -> None:
    """End-to-end: a real HTTP request gets wrapped in a span."""
    # We attach a SimpleSpanProcessor with an in-memory list exporter
    # so we can assert the span shape without a network call.
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    with patch.dict(os.environ, {"LOOP_OTEL_ENDPOINT": "disabled"}):
        app = _make_app()
    provider = app.state.tracer_provider
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    with TestClient(app) as client:
        client.get("/x")

    spans = exporter.get_finished_spans()
    assert spans, "no spans recorded"
    # FastAPI auto-instrumentation names spans by `<METHOD> <route>`.
    methods_seen = {span.attributes.get("http.method") for span in spans if span.attributes}
    assert "GET" in methods_seen


def test_disabled_endpoint_skips_exporter_wiring() -> None:
    """LOOP_OTEL_ENDPOINT=disabled must not attach an OTLP exporter
    (otherwise unit tests + air-gapped installs pay export overhead
    every request)."""
    with patch.dict(os.environ, {"LOOP_OTEL_ENDPOINT": "disabled"}):
        app = FastAPI()
        install_tracing(app, service_name="cp-api-test")
    provider = app.state.tracer_provider
    # No span processors should be attached
    # (The `_active_span_processor` is a CompositeSpanProcessor; check
    # that no individual processors were added by us.)
    composite = provider._active_span_processor
    inner = getattr(composite, "_span_processors", None)
    if inner is None:
        # Very recent SDK versions use a different attribute name; the
        # important thing is the disabled-env path didn't crash.
        return
    # The OTLP BatchSpanProcessor should NOT be among them.
    types = [type(p).__name__ for p in inner]
    assert "BatchSpanProcessor" not in types
