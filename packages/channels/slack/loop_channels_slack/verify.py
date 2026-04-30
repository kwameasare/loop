"""Slack request signature verification.

Per https://api.slack.com/authentication/verifying-requests-from-slack:
1. Read ``X-Slack-Request-Timestamp`` and reject if older than 5 minutes
   (replay protection).
2. Form ``v0:{timestamp}:{raw_body}`` and HMAC-SHA256 it with the
   workspace's signing secret.
3. Compare to ``X-Slack-Signature`` (which has a ``v0=`` prefix).
"""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Mapping

REPLAY_WINDOW_SECONDS = 5 * 60


class SignatureError(ValueError):
    """Raised when a Slack request fails verification."""


def verify_request(
    *,
    signing_secret: str,
    headers: Mapping[str, str],
    body: bytes,
    now: float | None = None,
) -> None:
    """Raise `SignatureError` if the request is not authentic."""
    if not signing_secret:
        raise SignatureError("signing_secret is empty")

    # Headers are case-insensitive on the wire; accept both forms.
    ts = headers.get("X-Slack-Request-Timestamp") or headers.get("x-slack-request-timestamp")
    sig = headers.get("X-Slack-Signature") or headers.get("x-slack-signature")
    if not ts or not sig:
        raise SignatureError("missing Slack signature headers")

    try:
        ts_int = int(ts)
    except ValueError as exc:
        raise SignatureError("non-integer timestamp") from exc

    current = now if now is not None else time.time()
    if abs(current - ts_int) > REPLAY_WINDOW_SECONDS:
        raise SignatureError("timestamp outside replay window")

    base = f"v0:{ts}:".encode() + body
    digest = hmac.new(signing_secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
    expected = f"v0={digest}"
    if not hmac.compare_digest(expected, sig):
        raise SignatureError("signature mismatch")


__all__ = ["REPLAY_WINDOW_SECONDS", "SignatureError", "verify_request"]
