"""OpenTelemetry tracing wiring for dp-runtime.

Closes P0.7c for the data plane. Mirrors
``loop_control_plane.tracing.install_tracing`` so the two services
emit spans against the same OTLP collector with distinct
``service.name`` resource attrs.

Notes
=====
* Auto-instruments the FastAPI app + httpx client (the gateway
  calls go through httpx, so the upstream LLM round-trip becomes
  a child span of the turn-handling span).
* Skipped entirely when ``LOOP_OTEL_ENDPOINT=disabled``.
"""

from __future__ import annotations

import os
from typing import Final

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

DEFAULT_OTLP_ENDPOINT: Final[str] = "http://localhost:4318/v1/traces"
SERVICE_NAME_DEFAULT: Final[str] = "dp-runtime"


def install_tracing(app: object, *, service_name: str = SERVICE_NAME_DEFAULT) -> None:
    """Wire OpenTelemetry FastAPI auto-instrumentation onto ``app``.

    See cp-api equivalent for env-var contract.
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
        export_url = (
            endpoint
            if endpoint.endswith("/v1/traces")
            else endpoint.rstrip("/") + "/v1/traces"
        )
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=export_url)))

    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)

    app._loop_tracing_installed = True  # type: ignore[attr-defined]
    app.state.tracer_provider = provider  # type: ignore[attr-defined]


__all__ = ["DEFAULT_OTLP_ENDPOINT", "SERVICE_NAME_DEFAULT", "install_tracing"]
