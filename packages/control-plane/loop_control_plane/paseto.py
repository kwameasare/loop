"""PASETO-shaped local token helper (S103).

Loop's choice of PASETO over JWT is documented in ADR-007 (alg-confusion
+ kid-shadowing risks). The full v4.local spec uses XChaCha20-Poly1305
which requires the ``cryptography`` package; that dependency lands when
the cp-api wheel is built. In the meantime this module ships a
*signed-but-not-encrypted* token that:

* matches the v4 token *shape* — ``v4.local.<base64url>.<base64url-footer>?``
* uses HMAC-SHA256 over header || payload || footer for authenticity
* embeds ``iat``/``nbf``/``exp`` claims with millisecond precision
* validates clock skew via ``leeway_ms`` (default 30 s)
* supports key rotation via the optional footer kid

This is sufficient for short-lived service-to-service tokens (Loop's
exchange flow rotates them every 15 minutes); customers MUST NOT use
the local-only tokens for confidentiality-sensitive claims.
"""

from __future__ import annotations

import base64
import hmac
import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

__all__ = [
    "PasetoError",
    "PasetoToken",
    "TokenExpired",
    "TokenInvalid",
    "TokenNotYetValid",
    "decode_local",
    "encode_local",
]

_HEADER = "v4.local."


class PasetoError(ValueError):
    """Base class for token errors."""


class TokenInvalid(PasetoError):  # noqa: N818 — domain-specific name; subclass of PasetoError.
    """Token failed structural or MAC validation."""


class TokenExpired(PasetoError):  # noqa: N818
    """Token's ``exp`` is in the past beyond the allowed leeway."""


class TokenNotYetValid(PasetoError):  # noqa: N818
    """Token's ``nbf`` is in the future beyond the allowed leeway."""


@dataclass(frozen=True)
class PasetoToken:
    claims: dict[str, Any]
    footer: dict[str, Any] | None
    kid: str | None


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def encode_local(
    claims: dict[str, Any],
    *,
    key: bytes,
    now_ms: int,
    expires_in_ms: int,
    not_before_ms: int = 0,
    footer: dict[str, Any] | None = None,
    kid: str | None = None,
) -> str:
    """Encode ``claims`` as a v4.local-shape token authenticated with ``key``.

    Reserved claims (``iat``/``nbf``/``exp``) are added; collisions in
    ``claims`` raise :class:`PasetoError`.
    """
    if len(key) < 32:
        raise PasetoError("key must be at least 32 bytes")
    if expires_in_ms <= 0:
        raise PasetoError("expires_in_ms must be positive")
    reserved = {"iat", "nbf", "exp"}
    if reserved & set(claims):
        raise PasetoError(f"claims may not contain reserved keys: {reserved}")
    full_claims = {
        **claims,
        "iat": now_ms,
        "nbf": now_ms + not_before_ms,
        "exp": now_ms + expires_in_ms,
    }
    payload = json.dumps(full_claims, separators=(",", ":"), sort_keys=True).encode()
    footer_obj = dict(footer or {})
    if kid is not None:
        footer_obj["kid"] = kid
    footer_bytes = (
        json.dumps(footer_obj, separators=(",", ":"), sort_keys=True).encode()
        if footer_obj
        else b""
    )
    mac = hmac.new(
        key, _HEADER.encode() + payload + footer_bytes, sha256
    ).digest()
    body = _b64url_encode(payload + mac)
    token = _HEADER + body
    if footer_bytes:
        token += "." + _b64url_encode(footer_bytes)
    return token


def decode_local(
    token: str,
    *,
    key: bytes,
    now_ms: int,
    leeway_ms: int = 30_000,
) -> PasetoToken:
    """Verify ``token`` against ``key`` and return the parsed claims.

    Raises :class:`TokenInvalid` on tampering, :class:`TokenExpired` /
    :class:`TokenNotYetValid` on temporal violations.
    """
    if not token.startswith(_HEADER):
        raise TokenInvalid("missing or wrong header")
    rest = token[len(_HEADER) :]
    parts = rest.split(".", 1)
    body_b64 = parts[0]
    footer_b64 = parts[1] if len(parts) == 2 else ""
    try:
        body = _b64url_decode(body_b64)
    except (ValueError, base64.binascii.Error) as exc:  # type: ignore[attr-defined]
        raise TokenInvalid("malformed body base64") from exc
    if len(body) <= 32:
        raise TokenInvalid("body too short")
    payload, mac = body[:-32], body[-32:]
    footer_bytes = _b64url_decode(footer_b64) if footer_b64 else b""
    expected = hmac.new(
        key, _HEADER.encode() + payload + footer_bytes, sha256
    ).digest()
    if not hmac.compare_digest(mac, expected):
        raise TokenInvalid("MAC mismatch")
    try:
        claims = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise TokenInvalid("payload is not valid JSON") from exc
    if not isinstance(claims, dict):
        raise TokenInvalid("payload must be a JSON object")
    nbf = claims.get("nbf")
    exp = claims.get("exp")
    if not isinstance(nbf, int) or not isinstance(exp, int):
        raise TokenInvalid("nbf/exp claims missing or not integers")
    if now_ms + leeway_ms < nbf:
        raise TokenNotYetValid(f"nbf={nbf} now={now_ms}")
    if now_ms - leeway_ms > exp:
        raise TokenExpired(f"exp={exp} now={now_ms}")
    footer_obj: dict[str, Any] | None = None
    kid: str | None = None
    if footer_bytes:
        try:
            footer_obj = json.loads(footer_bytes)
        except json.JSONDecodeError as exc:
            raise TokenInvalid("footer is not valid JSON") from exc
        if not isinstance(footer_obj, dict):
            raise TokenInvalid("footer must be a JSON object")
        kid_val = footer_obj.get("kid")
        if isinstance(kid_val, str):
            kid = kid_val
    return PasetoToken(claims=claims, footer=footer_obj, kid=kid)
