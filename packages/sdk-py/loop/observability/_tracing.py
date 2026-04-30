"""Tracer implementation -- thin wrapper around the OTel Python SDK.

The wrapper is deliberately small. Its job is **policy**, not abstraction:

  * Lock the set of span kinds to the canonical five
    (``llm`` / ``tool`` / ``retrieval`` / ``memory`` / ``channel``).
  * Provide a single ``async with tracer.span(...)`` entry point so that
    every call site looks the same.
  * Auto-record exceptions and stamp ``loop.error.code`` when the caller
    raises a ``LoopError``-shaped exception (duck-typed via ``code``
    attribute) -- the production error taxonomy lives in
    ``engineering/ERROR_CODES.md``.
  * Keep bootstrap (``init_tracing``) and test reset (``reset_for_test``)
    in the same file so the lifecycle is obvious.

Exporter selection:
  * If ``LOOP_OTEL_EXPORTER`` is unset or ``otlp``, install the OTLP/HTTP
    exporter pointed at ``LOOP_OTEL_ENDPOINT`` (default
    ``http://localhost:4318/v1/traces``). The local-dev collector
    (``infra/otel-collector.yaml``) terminates this endpoint and forwards
    to ClickHouse.
  * If set to ``memory``, install ``InMemorySpanExporter`` -- this is the
    fixture used by tests via :func:`reset_for_test`.
  * If set to ``none``, register no exporter (spans are dropped). Used in
    CI hot paths where we only want to assert API shape.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import AsyncIterator, Iterator
from typing import Any, Literal

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SpanExporter,
)
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.trace import Span as OtelSpan
from opentelemetry.trace import StatusCode

SpanKind = Literal["llm", "tool", "retrieval", "memory", "channel"]
_VALID_KINDS: frozenset[str] = frozenset(("llm", "tool", "retrieval", "memory", "channel"))

_DEFAULT_ENDPOINT = "http://localhost:4318/v1/traces"
_DEFAULT_SERVICE = "loop-runtime"

# Module-level state. Initialized lazily on first ``init_tracing()`` or
# ``reset_for_test()``; tests reset it to a known InMemoryExporter.
_provider: TracerProvider | None = None
_memory_exporter: InMemorySpanExporter | None = None


def _build_exporter() -> SpanExporter | None:
    mode = os.getenv("LOOP_OTEL_EXPORTER", "otlp").lower()
    if mode == "memory":
        return InMemorySpanExporter()
    if mode == "none":
        return None
    # Default: OTLP/HTTP. Imported lazily because it pulls in protobuf
    # bindings and we don't want every test boot paying for it.
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
        OTLPSpanExporter,
    )

    endpoint = os.getenv("LOOP_OTEL_ENDPOINT", _DEFAULT_ENDPOINT)
    return OTLPSpanExporter(endpoint=endpoint)


def init_tracing(
    service_name: str | None = None,
    *,
    extra_resource_attrs: dict[str, str] | None = None,
) -> TracerProvider:
    """Install a TracerProvider as the global OTel default.

    Idempotent: calling twice in the same process returns the existing
    provider so library code can safely call this from its own bootstrap.
    """
    global _provider, _memory_exporter
    if _provider is not None:
        return _provider

    resource_attrs: dict[str, Any] = {
        "service.name": service_name or os.getenv("LOOP_SERVICE_NAME", _DEFAULT_SERVICE),
        "service.version": os.getenv("LOOP_SERVICE_VERSION", "0.1.0"),
        "deployment.environment": os.getenv("LOOP_ENV", "dev"),
    }
    if extra_resource_attrs:
        resource_attrs.update(extra_resource_attrs)

    provider = TracerProvider(resource=Resource.create(resource_attrs))
    exporter = _build_exporter()
    if isinstance(exporter, InMemorySpanExporter):
        _memory_exporter = exporter
    if exporter is not None:
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _provider = provider
    return provider


def reset_for_test() -> InMemorySpanExporter:
    """Tear down any existing provider and install an in-memory exporter.

    Returns the exporter so tests can assert on the captured spans:

        exporter = reset_for_test()
        async with tracer.span("turn.execute", kind="llm") as s:
            s.set_attr("workspace_id", "w-1")
        spans = exporter.get_finished_spans()
        assert spans[0].name == "turn.execute"
    """
    global _provider, _memory_exporter
    if _provider is not None:
        _provider.shutdown()
    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": "test"}))
    # SimpleSpanProcessor would also work, but BatchSpanProcessor matches
    # production semantics; we force a flush in get_finished_spans().
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _provider = provider
    _memory_exporter = exporter
    return exporter


class _SpanHandle:
    """Tiny adapter so call sites use ``span.set_attr`` consistently."""

    __slots__ = ("_span",)

    def __init__(self, span: OtelSpan) -> None:
        self._span = span

    def set_attr(self, key: str, value: str | int | float | bool) -> None:
        self._span.set_attribute(key, value)

    def record_error_code(self, code: str) -> None:
        """Stamp the canonical error code attribute -- see ERROR_CODES.md."""
        self._span.set_attribute("loop.error.code", code)

    @property
    def raw(self) -> OtelSpan:
        return self._span


class Tracer:
    """The thin façade exported as ``tracer``."""

    def __init__(self, name: str = "loop") -> None:
        self._name = name

    @contextlib.contextmanager
    def span(
        self,
        name: str,
        *,
        kind: SpanKind,
        attrs: dict[str, str | int | float | bool] | None = None,
    ) -> Iterator[_SpanHandle]:
        """Sync context manager for synchronous code paths.

        Most call sites should use :meth:`aspan` -- this exists for the
        rare cases (CLI startup, sync tests) where async is awkward.
        """
        if kind not in _VALID_KINDS:
            raise ValueError(f"Invalid span kind {kind!r}; must be one of {sorted(_VALID_KINDS)}")
        provider = _provider if _provider is not None else trace.get_tracer_provider()
        otel = provider.get_tracer(self._name)
        with otel.start_as_current_span(name) as raw:
            raw.set_attribute("loop.span.kind", kind)
            for k, v in (attrs or {}).items():
                raw.set_attribute(k, v)
            handle = _SpanHandle(raw)
            try:
                yield handle
            except BaseException as exc:  # re-raised after recording
                code = getattr(exc, "code", None)
                if isinstance(code, str):
                    handle.record_error_code(code)
                raw.record_exception(exc)
                raw.set_status(StatusCode.ERROR, type(exc).__name__)
                raise

    @contextlib.asynccontextmanager
    async def aspan(
        self,
        name: str,
        *,
        kind: SpanKind,
        attrs: dict[str, str | int | float | bool] | None = None,
    ) -> AsyncIterator[_SpanHandle]:
        """Async context manager -- the canonical entry for runtime paths."""
        with self.span(name, kind=kind, attrs=attrs) as handle:
            yield handle


tracer = Tracer()


def get_finished_spans() -> list[ReadableSpan]:
    """Test helper -- returns spans recorded by the in-memory exporter."""
    if _memory_exporter is None:
        raise RuntimeError("No in-memory exporter installed; call reset_for_test() first.")
    return list(_memory_exporter.get_finished_spans())
