"""Tests for dp-runtime OpenTelemetry tracing wiring (P0.7c)."""

from __future__ import annotations

import os
from unittest.mock import patch

from fastapi import FastAPI
from loop_data_plane.tracing import install_tracing
from opentelemetry.sdk.trace import TracerProvider


def test_install_tracing_attaches_provider_with_dp_service_name() -> None:
    with patch.dict(os.environ, {"LOOP_OTEL_ENDPOINT": "disabled"}):
        app = FastAPI()
        install_tracing(app, service_name="dp-runtime-test")
    provider = app.state.tracer_provider
    assert isinstance(provider, TracerProvider)
    attrs = dict(provider.resource.attributes)
    assert attrs["service.name"] == "dp-runtime-test"


def test_install_tracing_idempotent() -> None:
    with patch.dict(os.environ, {"LOOP_OTEL_ENDPOINT": "disabled"}):
        app = FastAPI()
        install_tracing(app)
        install_tracing(app)
    assert hasattr(app.state, "tracer_provider")
