"""Cross-region telemetry PII filter (S596).

Loop pins each workspace to a single region (S/D/P-plane). Telemetry
spans, however, ride a global pipeline so SRE can see service-level
metrics from one pane of glass. That's the seam this module guards:
when a span row is about to leave its origin region, every attribute
must be either (a) a known structural metric (workspace_id, latency_ms,
status, etc.) or (b) explicitly redacted PII, never raw user content.

The default ``PIIScrubber`` is conservative: it drops any attribute key
matching a known-PII keyword (email, phone, msisdn, ip, name, prompt,
completion, request_body, response_body, …) and redacts free-form
attribute values that match canonical PII regexes. Callers wire it
into ``ClickHouseSpanExporter(pii_scrubber=..., cross_region=True)``;
constructing a cross-region exporter without a scrubber raises so a
careless deploy can't silently exfiltrate.

See ``loop_implementation/engineering/SECURITY.md`` §3.3.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

# Attribute keys that may carry PII — dropped wholesale rather than
# redacted, because partial redaction of a structured field is fragile.
_PII_KEY_TOKENS: frozenset[str] = frozenset(
    {
        "email",
        "phone",
        "msisdn",
        "ip",
        "ip_address",
        "user_name",
        "username",
        "full_name",
        "given_name",
        "family_name",
        "address",
        "ssn",
        "national_id",
        "credit_card",
        "card_number",
        "prompt",
        "completion",
        "request_body",
        "response_body",
        "user_input",
        "user_text",
        "message_text",
    }
)

# Structural attributes that always survive cross-region — the
# canonical metrics surface. Everything else falls through to the
# value-level scan.
_KEEP_KEYS: frozenset[str] = frozenset(
    {
        "workspace_id",
        "conversation_id",
        "turn_id",
        "trace_id",
        "span_id",
        "parent_span_id",
        "span_kind",
        "name",
        "started_at",
        "ended_at",
        "latency_ms",
        "cost_usd",
        "status",
        "loop.span.kind",
        "region",
        "tenant_id",
    }
)

_REDACTED = "<redacted-pii>"

# Free-form value patterns that must be redacted even if the attribute
# key was not on the drop list.
_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),  # email
    re.compile(r"\+?\d[\d\s().-]{8,}\d"),  # phone / msisdn
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # US SSN
    re.compile(r"\b(?:\d[ -]*?){13,19}\b"),  # PAN-like digit run
)


class PIIScrubber:
    """Filter a span row in place-safe (returns a new dict).

    Dropping an attribute is preferred over redaction because the
    cross-region telemetry contract is *metadata-only*: the receiving
    region must not be able to reconstruct user content even from
    aggregated runs.
    """

    def __init__(
        self,
        *,
        extra_drop_keys: Iterable[str] = (),
        extra_keep_keys: Iterable[str] = (),
    ) -> None:
        self._drop_tokens = _PII_KEY_TOKENS | {k.lower() for k in extra_drop_keys}
        self._keep = _KEEP_KEYS | set(extra_keep_keys)

    def scrub(self, row: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in row.items():
            if key == "attrs" and isinstance(value, dict):
                out[key] = self._scrub_attrs(value)
                continue
            out[key] = value
        return out

    def _scrub_attrs(self, attrs: dict[str, Any]) -> dict[str, Any]:
        cleaned: dict[str, Any] = {}
        for key, value in attrs.items():
            if key in self._keep:
                cleaned[key] = value
                continue
            if self._key_is_pii(key):
                cleaned[key] = _REDACTED
                continue
            cleaned[key] = self._scrub_value(value)
        return cleaned

    def _key_is_pii(self, key: str) -> bool:
        normalized = key.lower().replace(".", "_").replace("-", "_")
        return any(token in normalized for token in self._drop_tokens)

    def _scrub_value(self, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        for pattern in _VALUE_PATTERNS:
            if pattern.search(value):
                return _REDACTED
        return value


__all__ = ["PIIScrubber"]
