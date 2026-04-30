"""Web-channel security helpers (S172) and rate-limit composition (S174).

Two things plug into the web-channel front door:

1. ``CorsAllowlist`` -- exact-match origin checking. Wildcards (``*``)
   are intentionally rejected since the web-channel ships SSE which
   browsers gate behind credentials.
2. ``TurnTokenValidator`` -- HMAC-signed bearer token bound to a
   workspace_id + conversation_id so the SSE endpoint cannot be hit
   blind from a stolen workspace key.
3. ``WebChannelGuard`` -- glues the above with a ``RateLimiter`` keyed
   on (workspace_id, conversation_id).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from uuid import UUID

from loop_control_plane.rate_limit import RateLimiter

__all__ = [
    "CorsAllowlist",
    "TurnAuthError",
    "TurnTokenPayload",
    "TurnTokenValidator",
    "WebChannelGuard",
    "WebChannelGuardDecision",
]


class TurnAuthError(ValueError):
    """Raised on malformed, expired, or signature-invalid turn tokens."""


@dataclass(frozen=True)
class CorsAllowlist:
    """Exact-match origin allowlist. ``*`` is rejected at construction."""

    origins: frozenset[str]

    @classmethod
    def of(cls, origins: Iterable[str]) -> CorsAllowlist:
        normalised: list[str] = []
        for o in origins:
            if not o or "*" in o:
                raise ValueError(f"invalid CORS origin: {o!r}")
            normalised.append(o.rstrip("/"))
        return cls(origins=frozenset(normalised))

    def is_allowed(self, origin: str) -> bool:
        if not origin:
            return False
        return origin.rstrip("/") in self.origins


@dataclass(frozen=True)
class TurnTokenPayload:
    """The signed claims a web-channel turn carries."""

    workspace_id: UUID
    conversation_id: UUID
    issued_at_ms: int
    expires_at_ms: int


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _b64u_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


@dataclass
class TurnTokenValidator:
    """Compact HMAC-SHA256 token. Intentionally not a full JWT."""

    secret: bytes
    clock_ms: Callable[[], int] = field(
        default_factory=lambda: lambda: int(time.time() * 1000)
    )

    def __post_init__(self) -> None:
        if len(self.secret) < 32:
            raise ValueError("secret must be >= 32 bytes")

    def issue(
        self,
        *,
        workspace_id: UUID,
        conversation_id: UUID,
        ttl_ms: int = 5 * 60 * 1000,
    ) -> str:
        now = self.clock_ms()
        body = {
            "ws": str(workspace_id),
            "cv": str(conversation_id),
            "iat": now,
            "exp": now + ttl_ms,
        }
        payload = _b64u(json.dumps(body, separators=(",", ":")).encode("utf-8"))
        sig = _b64u(
            hmac.new(self.secret, payload.encode("ascii"), hashlib.sha256).digest()
        )
        return f"{payload}.{sig}"

    def verify(self, token: str) -> TurnTokenPayload:
        if token.count(".") != 1:
            raise TurnAuthError("malformed token")
        payload_b64, sig_b64 = token.split(".", 1)
        expected = _b64u(
            hmac.new(self.secret, payload_b64.encode("ascii"), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(expected, sig_b64):
            raise TurnAuthError("bad signature")
        try:
            body = json.loads(_b64u_decode(payload_b64).decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise TurnAuthError("malformed payload") from exc
        try:
            ws = UUID(body["ws"])
            cv = UUID(body["cv"])
            iat = int(body["iat"])
            exp = int(body["exp"])
        except (KeyError, ValueError, TypeError) as exc:
            raise TurnAuthError("missing/invalid claims") from exc
        if exp <= self.clock_ms():
            raise TurnAuthError("token expired")
        return TurnTokenPayload(
            workspace_id=ws,
            conversation_id=cv,
            issued_at_ms=iat,
            expires_at_ms=exp,
        )


@dataclass(frozen=True)
class WebChannelGuardDecision:
    """Combined CORS + auth + rate decision for a web-channel turn."""

    allowed: bool
    reason: str
    payload: TurnTokenPayload | None = None


@dataclass
class WebChannelGuard:
    """Gate every inbound web-channel turn through allowlist + token + rate."""

    cors: CorsAllowlist
    tokens: TurnTokenValidator
    limiter: RateLimiter

    async def admit(
        self,
        *,
        origin: str,
        token: str,
    ) -> WebChannelGuardDecision:
        if not self.cors.is_allowed(origin):
            return WebChannelGuardDecision(allowed=False, reason="cors_blocked")
        try:
            payload = self.tokens.verify(token)
        except TurnAuthError as exc:
            return WebChannelGuardDecision(allowed=False, reason=str(exc))
        key = f"web:{payload.workspace_id}:{payload.conversation_id}"
        ok = await self.limiter.try_consume(key)
        if not ok:
            return WebChannelGuardDecision(
                allowed=False, reason="rate_limited", payload=payload
            )
        return WebChannelGuardDecision(allowed=True, reason="ok", payload=payload)
