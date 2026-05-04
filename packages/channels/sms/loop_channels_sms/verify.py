"""Twilio webhook signature verification.

Closes P0.5b from the prod-readiness audit. Twilio signs every inbound
webhook with HMAC-SHA1 over a deterministically-canonicalised string
(URL + sorted form fields). The receiving service MUST verify the
``X-Twilio-Signature`` header before parsing — otherwise anyone with
the public webhook URL can spoof "incoming SMS" and trigger agent
runs billed to the operator's Twilio account.

See: https://www.twilio.com/docs/usage/webhooks/webhooks-security

Canonicalisation rule (Twilio docs §"Validate signature"):
    expected = base64(hmac_sha1(auth_token,
                                full_url + concat(sorted(form_fields))))
where each form field contributes ``key + value`` (no separator).

Notes
=====
* HMAC-SHA1 is what Twilio uses (legacy, but it's all they ship).
  We use ``hmac.compare_digest`` for constant-time comparison so a
  byte-by-byte timing attack on the auth-token can't extract it.
* JSON-bodied webhooks (``application/json`` notifications, not the
  default form-encoded SMS path) hash the JSON body string instead
  of the form fields. We support both via the ``body`` argument.
* ``valid_url`` is the FULL public URL Twilio used to call us —
  including any trailing query string. Don't pass the path-only;
  Twilio signs the entire URL it requested.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import Final

DEFAULT_MAX_SKEW_SECONDS: Final[int] = 600  # 10 minutes; Twilio's webhook
# delivery is meant to be fast, but their retries can land 10+ minutes
# late. We trade off replay window vs. retry success.

MAX_BODY_BYTES: Final[int] = 2 * 1024 * 1024


class TwilioSignatureError(ValueError):
    """Raised when an inbound Twilio webhook fails verification.

    Maps to HTTP 401. Generic message to avoid leaking which check
    failed.
    """


def _expected_signature_form(
    auth_token: str, url: str, form_fields: dict[str, str]
) -> str:
    """Compute the expected base64 HMAC-SHA1 for a form-encoded request.

    Twilio's canonicalisation: URL + concat of sorted-by-key (key+value)
    pairs.
    """
    payload = url
    for key in sorted(form_fields):
        payload += key + form_fields[key]
    digest = hmac.new(
        auth_token.encode("utf-8"), payload.encode("utf-8"), hashlib.sha1
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def _expected_signature_json(auth_token: str, url: str, body: bytes) -> str:
    """Compute the expected base64 HMAC-SHA1 for a JSON-bodied request.

    Twilio JSON webhooks (notifications, voice insights) sign the URL
    + body bytes.
    """
    payload = url.encode("utf-8") + body
    digest = hmac.new(auth_token.encode("utf-8"), payload, hashlib.sha1).digest()
    return base64.b64encode(digest).decode("ascii")


def verify_twilio_signature(
    *,
    auth_token: str,
    url: str,
    signature_header: str,
    form_fields: dict[str, str] | None = None,
    body: bytes | None = None,
    timestamp: str | None = None,
    max_skew_seconds: int = DEFAULT_MAX_SKEW_SECONDS,
    now: float | None = None,
) -> None:
    """Verify a Twilio webhook signature.

    Pass either ``form_fields`` (default form-encoded SMS path) or
    ``body`` (JSON notification path) — exactly one. Raises
    :class:`TwilioSignatureError` on any failure; returns normally on
    success.

    Optional ``timestamp`` (e.g. from a custom ``X-Loop-Webhook-Time``
    header set by the operator's reverse proxy) enables replay-window
    enforcement. Twilio doesn't send a timestamp themselves, so this
    is opt-in defense-in-depth: the operator should configure their
    edge proxy to stamp the request and gate on this.
    """
    if not auth_token or not url or not signature_header:
        raise TwilioSignatureError("invalid signature")
    if form_fields is None and body is None:
        raise TwilioSignatureError("invalid signature")
    if form_fields is not None and body is not None:
        raise TwilioSignatureError("invalid signature")

    if body is not None and len(body) > MAX_BODY_BYTES:
        raise TwilioSignatureError("body too large")

    if timestamp is not None:
        try:
            ts = int(timestamp)
        except (TypeError, ValueError) as exc:
            raise TwilioSignatureError("invalid signature") from exc
        current = now if now is not None else time.time()
        if abs(current - ts) > max_skew_seconds:
            raise TwilioSignatureError("invalid signature")

    if form_fields is not None:
        expected = _expected_signature_form(auth_token, url, form_fields)
    else:
        assert body is not None  # narrowed by branch
        expected = _expected_signature_json(auth_token, url, body)

    if not hmac.compare_digest(expected, signature_header):
        raise TwilioSignatureError("invalid signature")


__all__ = [
    "DEFAULT_MAX_SKEW_SECONDS",
    "TwilioSignatureError",
    "verify_twilio_signature",
]
