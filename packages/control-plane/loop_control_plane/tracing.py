"""OpenTelemetry tracing middleware for cp-api.

Closes P0.7c. Adds cross-service distributed tracing so a single
``request_id`` can be followed across cp-api → dp-runtime → gateway →
upstream LLM. Without it, debugging a prod incident requires log
correlation, which is fragile under high RPS.

What lands
==========
* :func:`install_tracing` — one-call wiring on a FastAPI app.
  Configures a :class:`TracerProvider` with the service-name resource
  attribute set, an OTLP HTTP exporter pointed at
  ``LOOP_OTEL_ENDPOINT`` (default ``http://localhost:4318``), and the
  FastAPI auto-instrumentation that creates one span per request.
* No-op when ``LOOP_OTEL_ENDPOINT=disabled`` so unit tests + air-gapped
  installs don't pay the export overhead.
* Idempotent — calling twice on the same app is fine.

The collector wiring in ``infra/otel-collector.yaml`` already routes
spans to Tempo / Jaeger / Honeycomb depending on the operator's
backend.
"""

from __future__ import annotations

import os
from typing import Final

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
)

DEFAULT_OTLP_ENDPOINT: Final[str] = "http://localhost:4318/v1/traces"
SERVICE_NAME_DEFAULT: Final[str] = "cp-api"


def install_tracing(app: object, *, service_name: str = SERVICE_NAME_DEFAULT) -> None:
    """Wire OpenTelemetry FastAPI auto-instrumentation onto ``app``.

    Reads ``LOOP_OTEL_ENDPOINT`` (default ``http://localhost:4318``)
    plus optional ``LOOP_SERVICE_VERSION`` (defaults to "0.0.0").
    Set ``LOOP_OTEL_ENDPOINT=disabled`` to skip exporter wiring
    entirely (unit tests, air-gapped installs).

    Idempotent — second call is a no-op.
    """
    from fastapi import FastAPI

    if not isinstance(app, FastAPI):
        raise TypeError("install_tracing requires a FastAPI app")
    if getattr(app, "_loop_tracing_installed", False):
        return

    endpoint = os.environ.get("LOOP_OTEL_ENDPOINT", DEFAULT_OTLP_ENDPOINT).strip()
    version = os.environ.get("LOOP_SERVICE_VERSION", "0.0.0").strip() or "0.0.0"
    deployment_env = os.environ.get("LOOP_ENV", "dev").strip() or "dev"

    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            SERVICE_VERSION: version,
            "deployment.environment": deployment_env,
        }
    )
    provider = TracerProvider(resource=resource)

    if endpoint.lower() != "disabled":
        # OTLP base URL convention: append /v1/traces if not already.
        export_url = (
            endpoint
            if endpoint.endswith("/v1/traces")
            else endpoint.rstrip("/") + "/v1/traces"
        )
        exporter = OTLPSpanExporter(endpoint=export_url)
        # SimpleSpanProcessor in tests for determinism would be ideal,
        # but we always go through Batch in production paths to avoid
        # per-request export latency. Tests stub with `disabled`.
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)

    # Auto-instrument: every FastAPI route gets a span named
    # `<METHOD> <path-template>`, with `http.status_code` etc.
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)

    app._loop_tracing_installed = True  # type: ignore[attr-defined]
    app.state.tracer_provider = provider  # type: ignore[attr-defined]


__all__ = ["DEFAULT_OTLP_ENDPOINT", "SERVICE_NAME_DEFAULT", "install_tracing"]
