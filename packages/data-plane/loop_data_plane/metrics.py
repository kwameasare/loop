"""Prometheus metrics middleware for the dp-runtime FastAPI app.

Closes P0.7b for the data plane. Mirrors
``loop_control_plane.metrics`` shape but with dp-prefixed metric names
so the two services don't collide if Prometheus scrapes them through
the same gateway.

Series exposed
==============
* ``loop_data_plane_requests_total{method, path, status_class}``
* ``loop_data_plane_request_duration_seconds{method, path}``
* ``loop_data_plane_turn_events_total{event_kind}`` — count of SSE
  events emitted per turn (``token``, ``tool_call``, ``complete``,
  ``error``, ``done``). Lets dashboards distinguish "5xx HTTP" from
  "200 OK with an SSE error frame" for the streaming path.
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

_REQUEST_COUNTER_NAME: Final[str] = "loop_data_plane_requests"
_REQUEST_DURATION_NAME: Final[str] = "loop_data_plane_request_duration_seconds"
_TURN_EVENT_COUNTER_NAME: Final[str] = "loop_data_plane_turn_events"

# Wider buckets than cp-api: dp serves SSE streams whose total duration
# is bounded by the underlying LLM call (typically 1–30s). The 60s
# bucket exists for genuinely slow paths (long tool execution).
_DEFAULT_BUCKETS: Final[tuple[float, ...]] = (
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0,
)


# Module-level counter for turn events, registered against a process-
# global registry. We don't gate on a per-app registry here because
# `_turns.py` calls `increment_turn_event(...)` from many code paths
# and we don't want every call site to thread a registry through.
_PROCESS_REGISTRY: CollectorRegistry | None = None
_TURN_EVENT_COUNTER: Counter | None = None


def _process_registry() -> CollectorRegistry:
    global _PROCESS_REGISTRY, _TURN_EVENT_COUNTER
    if _PROCESS_REGISTRY is None:
        _PROCESS_REGISTRY = CollectorRegistry()
    if _TURN_EVENT_COUNTER is None:
        _TURN_EVENT_COUNTER = Counter(
            _TURN_EVENT_COUNTER_NAME,
            "Total SSE turn events emitted by dp-runtime, by event kind.",
            ("event_kind",),
            registry=_PROCESS_REGISTRY,
        )
    return _PROCESS_REGISTRY


def _build_request_metrics(registry: CollectorRegistry) -> tuple[Counter, Histogram]:
    counter = Counter(
        _REQUEST_COUNTER_NAME,
        "Total HTTP requests served by dp-runtime.",
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
    """Counter + duration histogram for every HTTP request.

    Counter + histogram are pre-built in ``install_metrics`` and
    passed in here so install + middleware share the same registry
    slot (no duplicate-registration on retry).
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
        if request.url.path in ("/metrics", "/healthz"):
            return await call_next(request)
        start = time.perf_counter()
        path = _path_template(request)
        try:
            response = await call_next(request)
            self._counter.labels(
                method=request.method,
                path=path,
                status_class=_status_class(response.status_code),
            ).inc()
            self._histogram.labels(method=request.method, path=path).observe(
                time.perf_counter() - start
            )
            return response
        except Exception:
            self._counter.labels(
                method=request.method, path=path, status_class="5xx"
            ).inc()
            self._histogram.labels(method=request.method, path=path).observe(
                time.perf_counter() - start
            )
            raise


def increment_turn_event(event_kind: str) -> None:
    """Increment the per-event-kind counter. Called from the SSE
    streaming path in ``_turns.py``."""
    _process_registry()  # ensures _TURN_EVENT_COUNTER initialised
    assert _TURN_EVENT_COUNTER is not None
    _TURN_EVENT_COUNTER.labels(event_kind=event_kind).inc()


def install_metrics(app: object) -> None:
    """Mount the middleware + ``/metrics`` route. Idempotent."""
    from fastapi import FastAPI

    if not isinstance(app, FastAPI):
        raise TypeError("install_metrics requires a FastAPI app")
    if getattr(app, "_loop_metrics_installed", False):
        return
    request_registry = CollectorRegistry()
    counter, histogram = _build_request_metrics(request_registry)
    process_registry = _process_registry()
    app.state.metrics_registry = request_registry  # type: ignore[attr-defined]
    app.state.metrics_counter = counter  # type: ignore[attr-defined]
    app.state.metrics_histogram = histogram  # type: ignore[attr-defined]
    app.add_middleware(
        PrometheusMiddleware, counter=counter, histogram=histogram
    )

    async def metrics_endpoint(_request: Request) -> Response:
        # Concatenate per-app + process-global metrics into one
        # exposition body. Prometheus accepts the appended format.
        body = generate_latest(request_registry) + generate_latest(process_registry)
        return Response(content=body, media_type=CONTENT_TYPE_LATEST)

    app.add_route(
        "/metrics", metrics_endpoint, methods=["GET"], include_in_schema=False
    )
    app._loop_metrics_installed = True  # type: ignore[attr-defined]


__all__ = [
    "PrometheusMiddleware",
    "increment_turn_event",
    "install_metrics",
]
