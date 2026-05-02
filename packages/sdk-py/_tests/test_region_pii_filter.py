"""S596 — region: metadata-only telemetry (no PII) leaving region.

The cross-region telemetry pipeline MUST scrub PII before a span row
crosses the regional boundary. These tests pin the contract:

  * known PII attribute keys are dropped (replaced with the redaction
    sentinel) — happy path on a synthetic span carrying email, phone,
    msisdn, prompt text, request_body, and a free-form value with an
    embedded email;
  * structural metrics (workspace_id, latency_ms, span_kind, status)
    survive verbatim so the receiving region can still alert on them;
  * a cross-region exporter constructed without a scrubber is refused
    (failure mode — would silently exfiltrate PII).
"""

from __future__ import annotations

import json

import pytest
from loop.observability import (
    ClickHouseSpanExporter,
    PIIScrubber,
    reset_for_test,
    tracer,
)
from loop.observability.region_filter import _REDACTED  # type: ignore[attr-defined]
from opentelemetry.sdk.trace.export import SpanExportResult


def _span_with_synthetic_pii() -> None:
    with tracer.span(
        "turn.execute",
        kind="llm",
        attrs={
            "workspace_id": "11111111-1111-1111-1111-111111111111",
            "conversation_id": "22222222-2222-2222-2222-222222222222",
            "turn_id": "33333333-3333-3333-3333-333333333333",
            "cost_usd": 0.125,
            # Synthetic PII the filter MUST drop / redact.
            "user.email": "alice@example.com",
            "user.phone": "+1 415 555 0199",
            "msisdn": "27821234567",
            "prompt": "tell me about Bob who lives at 42 Main St",
            "request_body": '{"q":"hello"}',
            "free_form_note": "ping me at carol@example.com",
            # A non-PII free-form value must survive untouched.
            "model_id": "gpt-5",
        },
    ):
        pass


def test_cross_region_export_strips_pii_from_synthetic_span() -> None:
    exporter = reset_for_test()
    _span_with_synthetic_pii()

    sent: list[bytes] = []
    ch = ClickHouseSpanExporter(
        endpoint="http://clickhouse-eu:8123",
        transport=lambda url, body, timeout: sent.append(body),
        pii_scrubber=PIIScrubber(),
        cross_region=True,
    )

    result = ch.export(exporter.get_finished_spans())
    assert result is SpanExportResult.SUCCESS

    row = json.loads(sent[0].decode())
    attrs = row["attrs"]

    # Structural metrics survive — receiving region still sees the
    # span shape so SRE alerts work.
    assert row["workspace_id"] == "11111111-1111-1111-1111-111111111111"
    assert row["span_kind"] == "llm"
    assert row["status"] == "ok"
    assert int(row["latency_ms"]) >= 0
    assert attrs["cost_usd"] == "0.125"
    assert attrs["model_id"] == "gpt-5"

    # All known PII keys are redacted — no raw PII makes the trip.
    for pii_key in (
        "user.email",
        "user.phone",
        "msisdn",
        "prompt",
        "request_body",
    ):
        assert attrs[pii_key] == _REDACTED, f"{pii_key} leaked across region: {attrs[pii_key]!r}"

    # Free-form attribute whose value matches an email regex is
    # redacted by value scan even though its key isn't on the
    # PII list.
    assert attrs["free_form_note"] == _REDACTED

    # Belt-and-braces: the serialized payload must not contain any of
    # the synthetic PII literals.
    payload = sent[0].decode()
    for needle in (
        "alice@example.com",
        "carol@example.com",
        "+1 415 555 0199",
        "27821234567",
        "tell me about Bob",
        "42 Main St",
    ):
        assert needle not in payload, f"PII leaked across region: {needle!r}"


def test_cross_region_exporter_without_scrubber_is_refused() -> None:
    """Failure mode: misconfigured cross-region exporter must NOT
    silently fall back to passthrough. Refusing at construction time
    catches the deploy mistake at boot, not in production."""
    with pytest.raises(ValueError, match="cross_region=True requires a pii_scrubber"):
        ClickHouseSpanExporter(
            endpoint="http://clickhouse-eu:8123",
            cross_region=True,
        )


def test_in_region_exporter_unchanged_when_no_scrubber() -> None:
    """Sanity: in-region (default) exporter without a scrubber still
    works — we only enforce scrubbing on the cross-region seam."""
    exporter = reset_for_test()
    with tracer.span(
        "turn.execute",
        kind="llm",
        attrs={"workspace_id": "ws-1", "user.email": "alice@example.com"},
    ):
        pass

    sent: list[bytes] = []
    ch = ClickHouseSpanExporter(
        endpoint="http://clickhouse-local:8123",
        transport=lambda url, body, timeout: sent.append(body),
    )
    assert ch.export(exporter.get_finished_spans()) is SpanExportResult.SUCCESS
    # In-region path is unchanged: PII still present (this is the
    # local pipeline, not the cross-region one).
    assert "alice@example.com" in sent[0].decode()


def test_pii_scrubber_drops_phone_pattern_in_free_form_attrs() -> None:
    scrubber = PIIScrubber()
    row = {
        "workspace_id": "ws-1",
        "attrs": {
            "note": "call me at +1 415 555 0199 today",
            "model_id": "gpt-5",
        },
    }
    out = scrubber.scrub(row)
    assert out["attrs"]["note"] == _REDACTED
    assert out["attrs"]["model_id"] == "gpt-5"


def test_pii_scrubber_keeps_structural_keys_even_if_value_looks_pii() -> None:
    """Structural keys are on the keep-list so a workspace_id that
    happens to look like a phone number still survives."""
    scrubber = PIIScrubber()
    row = {
        "workspace_id": "11111111-1111-1111-1111-111111111111",
        "attrs": {
            "workspace_id": "11111111-1111-1111-1111-111111111111",
            "trace_id": "abc",
        },
    }
    out = scrubber.scrub(row)
    assert out["attrs"]["workspace_id"] == "11111111-1111-1111-1111-111111111111"
    assert out["attrs"]["trace_id"] == "abc"
