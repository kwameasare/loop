"""Webhook verification for the WhatsApp Cloud API.

Two flows:

- GET ``hub.challenge``: Meta sends a verification GET when the
  webhook is registered. We compare ``hub.verify_token`` against the
  configured token and return ``hub.challenge`` when it matches.

- POST ``X-Hub-Signature-256``: Each event POST is signed with
  ``sha256=<hex>`` over the raw request body using the app secret.
  We verify with ``hmac.compare_digest`` to avoid timing attacks.

Replay protection (P0.5f)
=========================
Meta does NOT send a per-request timestamp; signed payload covers only
the body. A captured webhook is therefore replayable forever. We
defend by extracting the in-payload event timestamps (Meta's
``entry[].changes[].value.messages[].timestamp`` / `statuses[].timestamp`,
unix seconds) and rejecting requests whose newest event is older than
``max_skew_seconds`` (default 10 minutes — Meta retries can land late).

This is opt-in via ``verify_event_timestamps`` so callers who genuinely
want to backfill historical events can disable.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import Mapping
from typing import Any, Final

DEFAULT_MAX_EVENT_SKEW_SECONDS: Final[int] = 600


class SignatureError(ValueError):
    """Raised when an inbound webhook fails signature verification."""


_HEADER_NAMES: tuple[str, ...] = (
    "X-Hub-Signature-256",
    "x-hub-signature-256",
)


def verify_challenge(
    *,
    expected_token: str,
    params: Mapping[str, str],
) -> str:
    """Verify a hub.challenge GET. Returns the challenge to echo."""
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    if mode != "subscribe" or token != expected_token or challenge is None:
        raise SignatureError("invalid challenge handshake")
    return challenge


def verify_signature(
    *,
    app_secret: str,
    headers: Mapping[str, str],
    body: bytes,
    verify_event_timestamps: bool = True,
    max_event_skew_seconds: int = DEFAULT_MAX_EVENT_SKEW_SECONDS,
    now: float | None = None,
) -> None:
    """Verify ``X-Hub-Signature-256`` against ``body``, plus optional
    replay-window check on the in-payload event timestamps.

    Raises ``SignatureError`` on any failure.

    Parameters
    ----------
    app_secret
        Meta app secret (NOT the verify-token).
    headers
        Request headers map (case-insensitive lookup of
        `X-Hub-Signature-256`).
    body
        Raw request bytes (do NOT re-encode after parsing).
    verify_event_timestamps
        Default True. Closes P0.5f: Meta-signed webhooks have no
        timestamp in the signature itself, so a captured webhook is
        replayable forever unless we gate on the per-event timestamp
        in the body. Disable only for backfill / testing flows.
    max_event_skew_seconds
        Reject when the newest event in the payload is older than
        this. Default 600s (10 min) — Meta delivery retries can land
        late but never that late.
    now
        Override for tests.
    """
    header: str | None = None
    for name in _HEADER_NAMES:
        if name in headers:
            header = headers[name]
            break
    if header is None:
        raise SignatureError("missing X-Hub-Signature-256 header")
    if not header.startswith("sha256="):
        raise SignatureError("malformed signature scheme")
    received = header[len("sha256=") :]
    expected = hmac.new(
        app_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(received, expected):
        raise SignatureError("signature mismatch")

    if verify_event_timestamps:
        _check_event_timestamp(body, max_event_skew_seconds, now)


def _check_event_timestamp(
    body: bytes, max_skew_seconds: int, now: float | None
) -> None:
    """Reject the request if every event in `body` is older than the
    skew window. Meta's payload shape:

        {
          "object": "whatsapp_business_account",
          "entry": [
            { "id": "...", "changes": [
                { "value": {
                    "messages": [
                      { "timestamp": "1700000000", ... }
                    ],
                    "statuses": [...]
                } }
            ] }
          ]
        }

    `timestamp` is unix seconds as a string. We pick the maximum across
    all messages + statuses; if every one is older than the window, we
    reject. If the body has no timestamps at all, skip (e.g. status-only
    payloads we can't gate on; Meta sends those with own timestamps).
    """
    try:
        payload = json.loads(body)
    except (ValueError, TypeError) as exc:
        raise SignatureError("body is not valid JSON") from exc

    timestamps = list(_walk_timestamps(payload))
    if not timestamps:
        # No timestamp present anywhere — can't gate. Don't reject:
        # the signature already proved provenance, and Meta has known
        # status-only shapes without timestamps. Defer to the caller's
        # own idempotency layer for replay defense in this case.
        return

    newest = max(timestamps)
    current = now if now is not None else time.time()
    if current - newest > max_skew_seconds:
        raise SignatureError("event timestamp outside replay window")


def _walk_timestamps(payload: Any) -> list[int]:
    """Yield all `timestamp` ints found in nested messages/statuses."""
    out: list[int] = []
    if not isinstance(payload, dict):
        return out
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            if not isinstance(change, dict):
                continue
            value = change.get("value") or {}
            if not isinstance(value, dict):
                continue
            for kind in ("messages", "statuses"):
                for evt in value.get(kind) or []:
                    if not isinstance(evt, dict):
                        continue
                    ts = evt.get("timestamp")
                    if isinstance(ts, str) and ts.isdigit():
                        out.append(int(ts))
                    elif isinstance(ts, int):
                        out.append(ts)
    return out


__all__ = [
    "DEFAULT_MAX_EVENT_SKEW_SECONDS",
    "SignatureError",
    "verify_challenge",
    "verify_signature",
]
