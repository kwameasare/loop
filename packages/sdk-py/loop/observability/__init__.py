"""Loop observability primitives -- the canonical tracer surface.

Every async path in Loop emits an OTel span; this module is the only
sanctioned source of those spans. Importers must use ``tracer.span(...)``
rather than calling ``opentelemetry`` directly so that:

  * The set of span kinds is policed (see ``SpanKind``).
  * Required attributes (``workspace_id``, ``conversation_id``, ...) are
    enforced at the seam where they are easiest to audit.
  * Tests can stand up an in-memory exporter via :func:`reset_for_test`
    instead of hitting an OTLP endpoint.

See ``loop_implementation/skills/observability/add-otel-span.md`` for the
golden-path checklist; ``loop_implementation/architecture/ARCHITECTURE.md``
section 7.5 for the broader observability story.
"""

from loop.observability._tracing import (
    SpanKind,
    Tracer,
    init_tracing,
    reset_for_test,
    tracer,
)

__all__ = ["SpanKind", "Tracer", "init_tracing", "reset_for_test", "tracer"]
