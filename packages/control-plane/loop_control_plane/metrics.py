"""Prometheus metrics middleware for the cp-api FastAPI app.

Closes P0.7b from the prod-readiness audit. Before this module
shipped, ``infra/prometheus/alerts/slo-burn.yaml`` referenced series
``loop_control_plane_requests_total``, ``loop_control_plane_request_duration_seconds``,
etc. — none of which were emitted. PagerDuty receivers were wired but
would never fire because the recording rules had no input.

What lands
==========
* :class:`PrometheusMiddleware` — Starlette middleware that increments
  a :class:`prometheus_client.Counter` per request and records duration
  in a :class:`prometheus_client.Histogram`. Labelled by method + path
  template + status class (2xx/3xx/4xx/5xx).
* :func:`metrics_endpoint` — a FastAPI route handler that serves
  ``/metrics`` in the Prometheus text exposition format.
* :func:`install_metrics` — one-call wiring helper for ``app.py``.

Why a custom middleware (vs starlette-prometheus, prometheus-fastapi-
instrumentator etc.)
=============================
Those libraries pull in a transitive grab-bag of deps and expose
implementation-leaky labels (full path, including parameter values).
We need exactly two metrics with stable cardinality so the Prometheus
storage doesn't explode on workspace-id-cardinality. Hand-rolled is
~50 LOC and bounded.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Final

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Service-prefixed names match the alerts in
# `infra/prometheus/alerts/slo-burn.yaml`. Don't rename without also
# updating the alert rules.
_REQUEST_COUNTER_NAME: Final[str] = "loop_control_plane_requests"
_REQUEST_DURATION_NAME: Final[str] = "loop_control_plane_request_duration_seconds"
# (the `_total` suffix is appended by prometheus_client automatically.)

# Histogram buckets calibrated for cp-api: read-mostly endpoints in the
# 5–500ms range, with a long tail to 5s for the rare slow path. Adjust
# if SLOs change.
_DEFAULT_BUCKETS: Final[tuple[float, ...]] = (
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0,
)


def _build_metrics(registry: CollectorRegistry) -> tuple[Counter, Histogram]:
    """Construct fresh metrics on a per-app registry.

    Per-app registry means tests can re-init repeatedly without
    colliding with the global default registry, and multiple
    co-running services in the same process don't share series.
    """
    counter = Counter(
        _REQUEST_COUNTER_NAME,
        "Total HTTP requests served by cp-api.",
        ("method", "path", "status_class"),
        registry=registry,
    )
    histogram = Histogram(
        _REQUEST_DURATION_NAME,
        "HTTP request duration in seconds, by method and path template.",
        ("method", "path"),
        buckets=_DEFAULT_BUCKETS,
        registry=registry,
    )
    return counter, histogram


def _path_template(request: Request) -> str:
    """Return the route's path template (`/v1/agents/{agent_id}`)
    rather than the literal path so cardinality stays bounded."""
    route = request.scope.get("route")
    if route is not None and hasattr(route, "path"):
        return str(route.path)
    return request.url.path


def _status_class(status_code: int) -> str:
    if 200 <= status_code < 300:
        return "2xx"
    if 300 <= status_code < 400:
        return "3xx"
    if 400 <= status_code < 500:
        return "4xx"
    if 500 <= status_code < 600:
        return "5xx"
    return "other"


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Increment counter + record duration for every request.

    Counter + histogram are constructed in ``install_metrics`` and
    passed in here, so install + middleware always share the same
    registry slot (no duplicate-registration on retry/restart).
    """

    def __init__(
        self,
        app: Callable[..., Awaitable[Response]],
        *,
        counter: Counter,
        histogram: Histogram,
    ) -> None:
        super().__init__(app)
        self._counter = counter
        self._histogram = histogram

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Skip /metrics itself so we don't pollute our own observability.
        if request.url.path in ("/metrics", "/healthz"):
            return await call_next(request)
        start = time.perf_counter()
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            # Re-raise after recording — Starlette's exception handlers
            # turn it into a 500 response we won't see here.
            self._counter.labels(
                method=request.method,
                path=_path_template(request),
                status_class="5xx",
            ).inc()
            self._histogram.labels(
                method=request.method, path=_path_template(request)
            ).observe(time.perf_counter() - start)
            raise
        self._counter.labels(
            method=request.method,
            path=_path_template(request),
            status_class=_status_class(status_code),
        ).inc()
        self._histogram.labels(
            method=request.method, path=_path_template(request)
        ).observe(time.perf_counter() - start)
        return response


def install_metrics(app: object) -> None:
    """Mount the middleware + ``/metrics`` route on a FastAPI app.

    Idempotent — calling twice (e.g. in tests) is fine; the second
    call is a no-op so we don't double-count requests or collide
    on registry registration.
    """
    from fastapi import FastAPI

    if not isinstance(app, FastAPI):
        raise TypeError("install_metrics requires a FastAPI app")
    if getattr(app, "_loop_metrics_installed", False):
        return
    registry = CollectorRegistry()
    counter, histogram = _build_metrics(registry)
    app.state.metrics_registry = registry  # type: ignore[attr-defined]
    app.state.metrics_counter = counter  # type: ignore[attr-defined]
    app.state.metrics_histogram = histogram  # type: ignore[attr-defined]
    app.add_middleware(
        PrometheusMiddleware, counter=counter, histogram=histogram
    )

    async def metrics_endpoint(_request: Request) -> Response:
        body = generate_latest(registry)
        return Response(content=body, media_type=CONTENT_TYPE_LATEST)

    app.add_route(
        "/metrics", metrics_endpoint, methods=["GET"], include_in_schema=False
    )
    app._loop_metrics_installed = True  # type: ignore[attr-defined]


__all__ = [
    "PrometheusMiddleware",
    "install_metrics",
]
