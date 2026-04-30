"""Webhook verification for the WhatsApp Cloud API.

Two flows:

- GET ``hub.challenge``: Meta sends a verification GET when the
  webhook is registered. We compare ``hub.verify_token`` against the
  configured token and return ``hub.challenge`` when it matches.

- POST ``X-Hub-Signature-256``: Each event POST is signed with
  ``sha256=<hex>`` over the raw request body using the app secret.
  We verify with ``hmac.compare_digest`` to avoid timing attacks.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping


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
) -> None:
    """Verify ``X-Hub-Signature-256`` against ``body``.

    Raises ``SignatureError`` on any failure.
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


__all__ = ["SignatureError", "verify_challenge", "verify_signature"]
