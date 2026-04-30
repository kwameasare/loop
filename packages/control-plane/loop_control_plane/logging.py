"""Structured logging with a request-scoped context (S102).

This module gives the control-plane API a single way to emit a JSON log
line per inbound request that always includes:

* ``request_id`` -- the value from ``X-Request-Id`` if present, else a
  freshly-generated UUID4 the caller is expected to echo back to the
  client.
* ``method`` -- HTTP method.
* ``path`` -- request path (without query string).
* ``status`` -- HTTP status code emitted by the handler.
* ``latency_ms`` -- wall-clock time spent inside ``RequestLogContext``.

It is *framework-agnostic*: the body of an HTTP middleware (FastAPI /
Starlette / aiohttp / vanilla ASGI) instantiates ``RequestLogContext``,
runs the handler inside the ``with`` block, and the line is emitted on
exit. ``X-Request-Id`` echo behaviour is the caller's responsibility --
the helper :func:`extract_request_id` returns the resolved id so the
middleware can put it on the response.

Why a context-var approach? structlog's ``contextvars`` integration
keeps every log line emitted *anywhere* during the request enriched
with the same ``request_id`` without callers having to thread a logger
explicitly. That matters because cp-api code reaches deep into the
control-plane services (workspaces, api_keys, billing, ...) which must
not import a web framework but still want their log lines stitched to
the originating request.
"""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from types import TracebackType
from typing import Any, Final, TextIO

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars
from structlog.stdlib import BoundLogger
from structlog.typing import EventDict, Processor, WrappedLogger

REQUEST_ID_HEADER: Final[str] = "X-Request-Id"
_REQUEST_ID_KEY: Final[str] = "request_id"
_DEFAULT_LOGGER_NAME: Final[str] = "loop.cp_api"


def extract_request_id(headers: Mapping[str, str]) -> str:
    """Resolve the request id for an incoming request.

    Header lookup is case-insensitive (the typical ASGI / FastAPI dict
    is already lowercase, but Starlette ``Headers`` and a bare ``dict``
    from a test fixture differ -- we tolerate both).
    """
    for key, value in headers.items():
        if key.lower() == REQUEST_ID_HEADER.lower():
            cleaned = value.strip()
            if cleaned:
                return cleaned
    return uuid.uuid4().hex


def configure_logging(
    *,
    level: int | str = logging.INFO,
    stream: TextIO | None = None,
    logger_name: str = _DEFAULT_LOGGER_NAME,
) -> BoundLogger:
    """Wire structlog -> stdlib -> JSON for the cp-api process.

    Idempotent: calling twice replaces the handler list with one fresh
    handler so test fixtures can call this in ``setup`` without
    leaking duplicate output.
    """
    target = stream if stream is not None else sys.stdout
    handler = logging.StreamHandler(target)
    handler.setFormatter(logging.Formatter("%(message)s"))

    root = logging.getLogger()
    root.handlers = [handler]
    if isinstance(level, str):
        root.setLevel(level.upper())
    else:
        root.setLevel(level)

    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(sort_keys=True),
    ]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            level if isinstance(level, int) else logging.getLevelName(level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(file=target),
        cache_logger_on_first_use=False,
    )
    return structlog.get_logger(logger_name)


def get_logger(name: str = _DEFAULT_LOGGER_NAME) -> BoundLogger:
    """Return a logger bound to ``name``; wraps :func:`structlog.get_logger`."""
    return structlog.get_logger(name)


class RequestLogContext:
    """Context manager that binds request metadata + emits one summary line.

    Usage::

        with RequestLogContext(method="GET", path="/v1/me",
                               headers=request.headers) as ctx:
            response = await handler(...)
            ctx.set_status(response.status_code)

    On exit, a single ``request.completed`` line is emitted carrying
    the bound metadata + the wall-clock latency. Any exception raised
    inside the block is recorded with ``status=500`` (callers can
    override via :meth:`set_status` before re-raising).

    The context object also exposes :attr:`request_id` so the middleware
    can echo it on the response.
    """

    __slots__ = (
        "_clock",
        "_logger",
        "_started_ns",
        "method",
        "path",
        "request_id",
        "status",
    )

    def __init__(
        self,
        *,
        method: str,
        path: str,
        headers: Mapping[str, str] | None = None,
        request_id: str | None = None,
        logger: BoundLogger | None = None,
        clock: Any = time.perf_counter_ns,
    ) -> None:
        self.method = method
        self.path = path
        if request_id is not None:
            self.request_id = request_id
        elif headers is not None:
            self.request_id = extract_request_id(headers)
        else:
            self.request_id = uuid.uuid4().hex
        self.status = 0
        self._logger = logger if logger is not None else get_logger()
        self._clock = clock
        self._started_ns = 0

    def __enter__(self) -> RequestLogContext:
        bind_contextvars(
            **{
                _REQUEST_ID_KEY: self.request_id,
                "method": self.method,
                "path": self.path,
            }
        )
        self._started_ns = int(self._clock())
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        latency_ms = max(0, (int(self._clock()) - self._started_ns) // 1_000_000)
        if exc is not None and self.status == 0:
            self.status = 500
        self._logger.info(
            "request.completed",
            method=self.method,
            path=self.path,
            status=self.status,
            latency_ms=latency_ms,
            request_id=self.request_id,
        )
        clear_contextvars()

    def set_status(self, status: int) -> None:
        """Record the HTTP status the handler produced."""
        self.status = int(status)


@contextmanager
def bound(**values: Any) -> Iterator[None]:
    """Temporarily bind extra fields to every log line in a block."""
    bind_contextvars(**values)
    try:
        yield
    finally:
        # We cannot ``clear_contextvars`` here without nuking the
        # outer ``RequestLogContext`` binding, so we instead pop the
        # specific keys we just added.
        for key in values:
            structlog.contextvars.unbind_contextvars(key)


# --------------------------------------------------------------------------- #
# Test helpers                                                                #
# --------------------------------------------------------------------------- #


class CapturingProcessor:
    """A structlog processor that buffers events for tests.

    Wire it via :func:`configure_for_capture`; the captured events are
    plain dicts so tests assert on keys without parsing JSON.
    """

    def __init__(self) -> None:
        self.events: list[EventDict] = []

    def __call__(
        self, logger: WrappedLogger, method_name: str, event_dict: EventDict
    ) -> str:
        self.events.append(dict(event_dict))
        return json.dumps(event_dict, sort_keys=True, default=str)


def configure_for_capture(
    *, level: int = logging.INFO, logger_name: str = _DEFAULT_LOGGER_NAME
) -> tuple[BoundLogger, CapturingProcessor]:
    """Configure structlog so a returned :class:`CapturingProcessor` records every event."""
    cap = CapturingProcessor()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            cap,  # final renderer => string output (discarded)
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=_NullStream()),
        cache_logger_on_first_use=False,
    )
    return structlog.get_logger(logger_name), cap


class _NullStream:
    """Discard stream used by :func:`configure_for_capture`."""

    def write(self, _: str) -> int:
        return 0

    def flush(self) -> None:
        return None


__all__ = [
    "REQUEST_ID_HEADER",
    "CapturingProcessor",
    "RequestLogContext",
    "bound",
    "configure_for_capture",
    "configure_logging",
    "extract_request_id",
    "get_logger",
]
