"""HTTP rate-limit middleware tests (vega #8).

Exercises the middleware against a small FastAPI app so we cover the
full ASGI path: bucket key composition, 429 envelope shape,
``Retry-After`` header, exempt-path bypass, principal resolution
order, and per-(principal, route_template) isolation.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from loop_control_plane.rate_limit import RateLimiter
from loop_control_plane.rate_limit_middleware import (
    RateLimitConfig,
    install_rate_limit,
)


def _principal_from_test_header(request) -> str:  # type: ignore[no-untyped-def]
    """Test-only principal resolver: pulls the workspace from a header.

    In production we'd use ``default_principal`` which reads
    ``request.state.workspace_id``, set by the auth middleware. The
    test can't easily set request.state from a sibling middleware
    because Starlette runs middlewares in LIFO order — so we shortcut
    via a dedicated header instead."""
    ws = request.headers.get("x-test-workspace")
    if ws:
        return f"ws:{ws}"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    if request.client is not None and request.client.host:
        return f"ip:{request.client.host}"
    return "anonymous"


def _app(*, capacity: float, refill_per_sec: float) -> FastAPI:
    app = FastAPI()

    @app.get("/v1/agents/{agent_id}")
    async def get_agent(agent_id: str) -> dict[str, str]:
        return {"id": agent_id}

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    install_rate_limit(
        app,
        limiter=RateLimiter(capacity=capacity, refill_per_sec=refill_per_sec),
        config=RateLimitConfig(capacity=capacity, refill_per_sec=refill_per_sec),
        principal_fn=_principal_from_test_header,
    )
    return app


def test_within_capacity_returns_200() -> None:
    app = _app(capacity=5, refill_per_sec=1)
    client = TestClient(app)
    for _ in range(5):
        r = client.get("/v1/agents/a", headers={"x-test-workspace": "ws-1"})
        assert r.status_code == 200


def test_over_capacity_returns_429_with_envelope_and_retry_after() -> None:
    app = _app(capacity=2, refill_per_sec=1)
    client = TestClient(app)
    for _ in range(2):
        ok = client.get("/v1/agents/a", headers={"x-test-workspace": "ws-1"})
        assert ok.status_code == 200
    over = client.get("/v1/agents/a", headers={"x-test-workspace": "ws-1"})
    assert over.status_code == 429
    body = over.json()
    assert body["code"] == "LOOP-RL-001"
    assert "rate limit" in body["message"].lower()
    assert int(over.headers["Retry-After"]) >= 1
    assert body["retry_after_seconds"] >= 1


def test_exempt_paths_are_not_counted() -> None:
    """``/healthz`` etc must never trip the limiter — kubelet probes
    would knock the whole service offline otherwise."""
    app = _app(capacity=1, refill_per_sec=0.001)
    client = TestClient(app)
    for _ in range(50):
        r = client.get("/healthz")
        assert r.status_code == 200


def test_per_workspace_isolation() -> None:
    """Two workspaces hitting the same route must NOT share a bucket
    — that's the whole point of including the principal in the key."""
    app = _app(capacity=1, refill_per_sec=0.001)
    client = TestClient(app)
    # Workspace A burns its single token.
    a_first = client.get("/v1/agents/a", headers={"x-test-workspace": "ws-a"})
    a_second = client.get("/v1/agents/a", headers={"x-test-workspace": "ws-a"})
    assert a_first.status_code == 200
    assert a_second.status_code == 429
    # Workspace B is unaffected.
    b_first = client.get("/v1/agents/a", headers={"x-test-workspace": "ws-b"})
    assert b_first.status_code == 200


def test_per_route_template_isolation() -> None:
    """Different routes use different buckets (otherwise a noisy
    /v1/turns endpoint would starve /v1/agents)."""
    app = FastAPI()

    @app.get("/v1/agents")
    async def list_agents() -> list[str]:
        return []

    @app.get("/v1/turns")
    async def list_turns() -> list[str]:
        return []

    install_rate_limit(
        app,
        limiter=RateLimiter(capacity=1, refill_per_sec=0.001),
        config=RateLimitConfig(capacity=1, refill_per_sec=0.001),
        principal_fn=lambda _request: "ws:ws-c",
    )
    client = TestClient(app)
    assert client.get("/v1/agents").status_code == 200
    # /v1/agents is now exhausted but /v1/turns should still have a token.
    assert client.get("/v1/agents").status_code == 429
    assert client.get("/v1/turns").status_code == 200


def test_falls_back_to_ip_for_unauthenticated_requests() -> None:
    """No ``request.state.workspace_id`` → keyed on client IP. This is
    what bounds credential-stuffing on /v1/auth/login."""
    app = FastAPI()

    @app.get("/v1/auth/login")
    async def login() -> dict[str, str]:
        return {"status": "ok"}

    install_rate_limit(
        app,
        limiter=RateLimiter(capacity=1, refill_per_sec=0.001),
        config=RateLimitConfig(capacity=1, refill_per_sec=0.001),
    )
    client = TestClient(app)
    # First call from "the same IP" is admitted; the second 429s.
    assert client.get("/v1/auth/login").status_code == 200
    assert client.get("/v1/auth/login").status_code == 429


def test_install_is_idempotent() -> None:
    """Calling install twice must not double-wrap the app — otherwise
    each request would consume two tokens silently."""
    app = FastAPI()

    @app.get("/x")
    async def x() -> dict[str, str]:
        return {}

    rl1 = install_rate_limit(app, limiter=RateLimiter(capacity=10, refill_per_sec=1))
    rl2 = install_rate_limit(app, limiter=RateLimiter(capacity=99, refill_per_sec=99))
    assert rl1 is rl2
    # The second install was a no-op, so the original limiter (10 cap)
    # is still the one in effect.
    client = TestClient(app)
    for _ in range(10):
        assert client.get("/x").status_code == 200
    assert client.get("/x").status_code == 429
