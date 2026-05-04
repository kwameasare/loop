"""Discord interactions webhook signature verification.

Closes P0.5a from the prod-readiness audit: Discord's Interactions API
ships an `X-Signature-Ed25519` + `X-Signature-Timestamp` pair on every
inbound webhook; the receiving service must verify the ed25519
signature against the application's public key before processing.
Without this, anyone with the public key (which is not a secret) plus
a chosen-prefix attack can spoof inbound interactions and trigger
agent runs as if Discord sent them.

See: https://discord.com/developers/docs/interactions/receiving-and-responding#security-and-authorization

Design notes
============
* The verifier is a thin function so callers can adopt it from any
  HTTP framework (FastAPI / Starlette / aiohttp).
* The public key is hex-encoded in the Discord developer dashboard;
  we accept either hex or raw bytes for ergonomics.
* We treat any verification error (bad signature, malformed key,
  expired timestamp) as a hard reject — never a fall-through. The
  caller is responsible for returning HTTP 401 to Discord.
* Replay window: Discord doesn't strictly require a timestamp window
  on inbound (their advice is "verify the signature, that's enough")
  but production callers should add their own window since the
  signed payload includes the timestamp string. We expose the
  `max_skew_seconds` knob (default 5 min) and verify it.

Tests live under ``packages/channels/discord/_tests/test_verify.py``
and use deterministic ed25519 keys so they're hermetic.
"""

from __future__ import annotations

import hmac as _hmac
import time
from typing import Final

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

# Discord's docs are loose on max body size for interactions; 2 MB is
# a defensive cap and roughly matches what their gateway tolerates.
MAX_BODY_BYTES: Final[int] = 2 * 1024 * 1024
DEFAULT_MAX_SKEW_SECONDS: Final[int] = 300


class DiscordSignatureError(ValueError):
    """Raised when an inbound Discord webhook fails verification.

    Maps cleanly to HTTP 401 in any web framework. The exception
    message is intentionally generic so we don't tell an attacker
    *which* check failed (signature vs. timestamp vs. key shape).
    """


def _normalise_public_key(public_key: str | bytes) -> bytes:
    """Accept hex (Discord dashboard format) or raw 32-byte key."""
    if isinstance(public_key, str):
        try:
            return bytes.fromhex(public_key)
        except ValueError as exc:
            raise DiscordSignatureError("invalid public key") from exc
    if len(public_key) != 32:
        raise DiscordSignatureError("invalid public key")
    return public_key


def verify_discord_signature(
    *,
    body: bytes,
    signature_hex: str,
    timestamp: str,
    public_key: str | bytes,
    max_skew_seconds: int = DEFAULT_MAX_SKEW_SECONDS,
    now: float | None = None,
) -> None:
    """Verify a Discord interactions webhook.

    Raises :class:`DiscordSignatureError` on any failure. Returns
    normally on success — callers should treat any raise as HTTP 401.

    Args
    ----
    body
        Raw request body bytes (must NOT be re-encoded JSON; pass the
        exact bytes that came over the wire so the signed message
        matches).
    signature_hex
        Value of the ``X-Signature-Ed25519`` header.
    timestamp
        Value of the ``X-Signature-Timestamp`` header (a unix epoch
        string).
    public_key
        Discord application's public key (hex string from the dashboard
        or 32 raw bytes).
    max_skew_seconds
        Reject if ``abs(now - timestamp) > max_skew_seconds``. Default
        300s.
    now
        Override for tests. Defaults to ``time.time()``.
    """
    if len(body) > MAX_BODY_BYTES:
        raise DiscordSignatureError("body too large")

    # Timestamp window — guards against replay of an old captured
    # webhook. Discord sends a unix epoch as a string.
    try:
        ts = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise DiscordSignatureError("invalid signature") from exc
    current = now if now is not None else time.time()
    if abs(current - ts) > max_skew_seconds:
        raise DiscordSignatureError("invalid signature")

    # Signature verification proper. Discord's signed message is
    # `timestamp || body`. Use constant-time comparisons via
    # cryptography's verifier (which handles equal-length compare
    # internally). We also reject malformed hex up-front.
    try:
        signature = bytes.fromhex(signature_hex)
    except (TypeError, ValueError) as exc:
        raise DiscordSignatureError("invalid signature") from exc
    if len(signature) != 64:
        raise DiscordSignatureError("invalid signature")

    key_bytes = _normalise_public_key(public_key)
    try:
        verifier = Ed25519PublicKey.from_public_bytes(key_bytes)
    except (ValueError, TypeError) as exc:
        raise DiscordSignatureError("invalid public key") from exc

    message = timestamp.encode("utf-8") + body
    try:
        verifier.verify(signature, message)
    except InvalidSignature as exc:
        raise DiscordSignatureError("invalid signature") from exc


def constant_time_eq(a: bytes, b: bytes) -> bool:
    """Re-export of ``hmac.compare_digest`` so callers don't have to
    re-import; useful for constant-time comparisons of ancillary
    fields (interaction tokens, etc.) sharing the same module.
    """
    return _hmac.compare_digest(a, b)


__all__ = [
    "DEFAULT_MAX_SKEW_SECONDS",
    "DiscordSignatureError",
    "constant_time_eq",
    "verify_discord_signature",
]
