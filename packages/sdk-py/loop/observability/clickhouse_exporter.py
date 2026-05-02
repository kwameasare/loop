from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import StatusCode

from loop.observability.region_filter import PIIScrubber


class ClickHouseSpanExporter(SpanExporter):
    def __init__(
        self,
        *,
        endpoint: str,
        table: str = "otel_traces",
        timeout_seconds: float = 5.0,
        transport: Callable[[str, bytes, float], None] | None = None,
        pii_scrubber: PIIScrubber | None = None,
        cross_region: bool = False,
    ) -> None:
        if not endpoint.startswith(("http://", "https://")):
            raise ValueError("endpoint must use http or https")
        if cross_region and pii_scrubber is None:
            # S596: a cross-region exporter MUST run a PII scrubber.
            # Refuse to construct rather than silently exfiltrate.
            raise ValueError("cross_region=True requires a pii_scrubber")
        self._endpoint = endpoint.rstrip("/")
        self._table = table
        self._timeout = timeout_seconds
        self._transport = transport or _http_post
        self._scrubber = pii_scrubber

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if not spans:
            return SpanExportResult.SUCCESS
        rows = [_span_to_row(span) for span in spans]
        if self._scrubber is not None:
            rows = [self._scrubber.scrub(row) for row in rows]
        body = "\n".join(json.dumps(row, sort_keys=True) for row in rows)
        query = urlencode({"query": f"INSERT INTO {self._table} FORMAT JSONEachRow"})
        try:
            self._transport(f"{self._endpoint}/?{query}", body.encode(), self._timeout)
        except (OSError, URLError, RuntimeError):
            return SpanExportResult.FAILURE
        return SpanExportResult.SUCCESS

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        _ = timeout_millis  # API compatibility; exports are synchronous.
        return True


def _http_post(url: str, body: bytes, timeout_seconds: float) -> None:
    request = Request(  # noqa: S310 - exporter validates http/https endpoint.
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=timeout_seconds):  # noqa: S310
        pass


def _span_to_row(span: ReadableSpan) -> dict[str, Any]:
    attrs = {str(k): str(v) for k, v in (span.attributes or {}).items()}
    context = span.context
    parent = span.parent
    started_at = span.start_time or 0
    ended_at = span.end_time or span.start_time or 0
    row: dict[str, Any] = {
        "workspace_id": attrs.get("workspace_id", ""),
        "conversation_id": attrs.get("conversation_id", ""),
        "turn_id": attrs.get("turn_id", ""),
        "trace_id": f"{context.trace_id:032x}",
        "span_id": f"{context.span_id:016x}",
        "parent_span_id": f"{parent.span_id:016x}" if parent else "",
        "span_kind": attrs.get("loop.span.kind", ""),
        "name": span.name,
        "started_at": _format_ch_time(started_at),
        "ended_at": _format_ch_time(ended_at),
        "latency_ms": max(0, int((ended_at - started_at) / 1_000_000)),
        "cost_usd": attrs.get("cost_usd", "0"),
        "status": "error" if span.status.status_code is StatusCode.ERROR else "ok",
        "attrs": attrs,
    }
    return row


def _format_ch_time(value: int) -> str:
    return datetime.fromtimestamp(value / 1_000_000_000, tz=UTC).strftime("%Y-%m-%d %H:%M:%S.%f")[
        :-3
    ]


__all__ = ["ClickHouseSpanExporter"]
