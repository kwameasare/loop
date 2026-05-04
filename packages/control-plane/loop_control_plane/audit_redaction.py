"""Redaction registry for persisted audit payloads.

Audit payloads are stored for SOC2 replay, so callers may include useful
request/response context here. Sensitive values must be removed before the
payload is hashed or persisted.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

REDACTED = "[REDACTED]"

_SENSITIVE_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "audio_url",
        "authorization",
        "key",
        "new_value",
        "password",
        "plain_text",
        "plaintext",
        "recording_download_url",
        "recording_signed_url",
        "recording_url",
        "refresh_token",
        "secret",
        "signed_recording_url",
        "token",
        "value",
    }
)


def _normalise_key(key: object) -> str:
    return str(key).strip().lower().replace("-", "_")


def redact_for_audit(payload: object) -> object:
    """Return a JSON-shaped copy with sensitive fields replaced."""
    if isinstance(payload, Mapping):
        redacted: dict[str, object] = {}
        for key, value in payload.items():
            name = _normalise_key(key)
            if name in _SENSITIVE_KEYS:
                if isinstance(value, Mapping) or (
                    isinstance(value, Sequence)
                    and not isinstance(value, str | bytes | bytearray)
                ):
                    redacted[str(key)] = redact_for_audit(value)
                else:
                    redacted[str(key)] = REDACTED
            else:
                redacted[str(key)] = redact_for_audit(value)
        return redacted
    if isinstance(payload, tuple):
        return [redact_for_audit(item) for item in payload]
    if isinstance(payload, Sequence) and not isinstance(payload, str | bytes | bytearray):
        return [redact_for_audit(item) for item in payload]
    if isinstance(payload, bytes | bytearray):
        return REDACTED
    return payload


__all__ = ["REDACTED", "redact_for_audit"]
