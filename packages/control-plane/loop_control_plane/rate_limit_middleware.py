"""ASGI middleware: per-(principal, route_template) HTTP rate limiting.

Closes vega #8 (block-prod): the cp + dp HTTP services had no
incoming-request rate limit. A noisy tenant or a runaway client could
saturate the API server, starving every other workspace. We had a
turn-admission token bucket on the runtime path
(``loop_runtime.turn_rate_limit``) and per-tenant plan limits in the
billing layer, but no defense at the HTTP boundary.

The middleware is small + framework-agnostic — it's a standard
:class:`starlette.middleware.base.BaseHTTPMiddleware` wrapping the
existing :class:`loop_control_plane.rate_limit.RateLimiter`. The same
class is mounted on cp and dp via the helpers below; gateway-style
internal callers can still reach the underlying ``RateLimiter`` if
they want admission gating without HTTP.

Bucket key shape: ``rl:{principal}:{method}:{path_template}``. The
principal is whatever the caller resolved (workspace_id from cp's
api-key middleware, sub from dp's JWT, or the client IP for
unauthenticated paths). Keying on the path **template** (not the
fully expanded URL) means ``/v1/agents/{id}`` shares one bucket per
workspace instead of one bucket per agent — which is what you want
for hot-tenant defense.

A 429 carries:

  - Standard ``Retry-After`` header (seconds, integer).
  - Loop error envelope ``{"code": "LOOP-RL-001", "message": ...}`` so
    clients can map it through the same handler that consumes
    ``LOOP-GW-301`` etc.
"""

from __future__ import annotations

import math
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Final

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match

from loop_control_plane.rate_limit import RateLimiter

__all__ = [
    "RateLimitMiddleware",
    "RateLimitConfig",
    "default_principal",
]

_DEFAULT_EXEMPT_PATHS: Final = frozenset(
    {"/metrics", "/healthz", "/livez", "/readyz"}
)


@dataclass(frozen=True)
class RateLimitConfig:
    """Per-mount rate-limit knobs.

    Args:
        capacity: bucket size (burst tolerance).
        refill_per_sec: steady-state requests/sec.
        exempt_paths: paths that bypass the limiter entirely (health,
            metrics). Compared by exact match against ``request.url.path``.
        cost: how many tokens each accepted request consumes. Stays at
            1.0 unless a route is meaningfully more expensive (we don't
            currently special-case any).
    """

    capacity: float = 60.0
    refill_per_sec: float = 30.0
    exempt_paths: frozenset[str] = _DEFAULT_EXEMPT_PATHS
    cost: float = 1.0


def default_principal(request: Request) -> str:
    """Extract a stable identifier for bucket keying.

    Order of precedence:

    1. ``request.state.workspace_id`` if set by an upstream auth
       middleware (cp's ApiKeyMiddleware, dp's JWT decoder).
    2. ``X-Forwarded-For`` first hop, since cp + dp run behind
       ingress/CDN.
    3. ``request.client.host``.
    4. The literal string ``anonymous``.

    Returning the IP for unauthenticated traffic is intentional: it
    rate-limits ``/v1/auth/login`` against credential-stuffing without
    a workspace id.
    """
    workspace_id = getattr(request.state, "workspace_id", None)
    if workspace_id:
        return f"ws:{workspace_id}"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    if request.client is not None and request.client.host:
        return f"ip:{request.client.host}"
    return "anonymous"


def _path_template(request: Request) -> str:
    """Resolve the matched route's path template (e.g.
    ``/v1/agents/{id}``). Keying on the template means the bucket
    bounds the *aggregate* of all expansions for that route, which is
    the right granularity for hot-tenant defense.

    Falls back to the raw URL path if the route isn't matched yet
    (e.g. a 404 path before the router runs).
    """
    for route in request.app.routes:
        match, _scope = route.matches(request.scope)
        if match == Match.FULL:
            template = getattr(route, "path", None)
            if isinstance(template, str):
                return template
    return request.url.path


class RateLimitMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that consults a token bucket per
    (principal, method, path_template) before admitting a request.

    Both cp and dp mount this; the bucket store is in-memory by
    default and gets swapped for Redis in production via
    :class:`loop_control_plane.rate_limit.RateLimiter`'s pluggable
    backend (already used by the turn admission limiter)."""

    def __init__(
        self,
        app: Callable[..., Awaitable[Response]],
        *,
        limiter: RateLimiter,
        config: RateLimitConfig | None = None,
        principal_fn: Callable[[Request], str] = default_principal,
    ) -> None:
        super().__init__(app)
        self._limiter = limiter
        self._config = config or RateLimitConfig()
        self._principal_fn = principal_fn

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path in self._config.exempt_paths:
            return await call_next(request)
        principal = self._principal_fn(request)
        path = _path_template(request)
        bucket_key = f"rl:{principal}:{request.method}:{path}"
        admitted = await self._limiter.try_consume(
            bucket_key, cost=self._config.cost
        )
        if admitted:
            return await call_next(request)
        retry_after = _retry_after_seconds(self._config, self._limiter)
        return JSONResponse(
            status_code=429,
            content={
                "code": "LOOP-RL-001",
                "message": "rate limit exceeded",
                "retry_after_seconds": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )


def _retry_after_seconds(config: RateLimitConfig, limiter: RateLimiter) -> int:
    """Conservative ``Retry-After`` hint: how long until one full token
    refills, ceil'd to a whole second. We bias high (ceil) so clients
    don't retry the moment they read the header and immediately
    bounce off a still-empty bucket."""
    if limiter.refill_per_sec <= 0:
        # Bucket never refills (mis-config). Tell clients to back off
        # well past the typical retry window.
        return 60
    seconds = config.cost / limiter.refill_per_sec
    return max(1, math.ceil(seconds))


def install_rate_limit(
    app: object,
    *,
    limiter: RateLimiter | None = None,
    config: RateLimitConfig | None = None,
    principal_fn: Callable[[Request], str] = default_principal,
    exempt_paths: Iterable[str] | None = None,
) -> RateLimiter:
    """Mount the middleware on a FastAPI app. Idempotent.

    Returns the limiter so callers can introspect bucket state in tests
    or wire it into admin endpoints. Production should pass an explicit
    ``limiter`` backed by Redis; tests get the in-memory default.
    """
    from fastapi import FastAPI

    if not isinstance(app, FastAPI):
        raise TypeError("install_rate_limit requires a FastAPI app")
    if getattr(app, "_loop_rate_limit_installed", False):
        return app.state.rate_limiter  # type: ignore[no-any-return]

    cfg = config or RateLimitConfig()
    if exempt_paths is not None:
        cfg = RateLimitConfig(
            capacity=cfg.capacity,
            refill_per_sec=cfg.refill_per_sec,
            exempt_paths=frozenset(exempt_paths) | _DEFAULT_EXEMPT_PATHS,
            cost=cfg.cost,
        )

    rl = limiter or RateLimiter(
        capacity=cfg.capacity, refill_per_sec=cfg.refill_per_sec
    )
    app.state.rate_limiter = rl  # type: ignore[attr-defined]
    app.add_middleware(
        RateLimitMiddleware,
        limiter=rl,
        config=cfg,
        principal_fn=principal_fn,
    )
    app._loop_rate_limit_installed = True  # type: ignore[attr-defined]
    return rl
