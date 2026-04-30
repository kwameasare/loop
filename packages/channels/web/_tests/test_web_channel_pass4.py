"""Tests for pass4 web-channel substance: S172 CORS+token, S174 rate limit."""

from __future__ import annotations

import secrets
from uuid import uuid4

import pytest
from loop_channels_web.security import (
    CorsAllowlist,
    TurnAuthError,
    TurnTokenValidator,
    WebChannelGuard,
)
from loop_control_plane.rate_limit import RateLimiter


# --------------------------------------------------------------- S172 CORS
def test_cors_allowlist_exact_match_only() -> None:
    al = CorsAllowlist.of(["https://app.example.com"])
    assert al.is_allowed("https://app.example.com")
    assert al.is_allowed("https://app.example.com/")  # trailing-slash normalised
    assert not al.is_allowed("https://evil.example.com")
    assert not al.is_allowed("")


def test_cors_allowlist_rejects_wildcards_at_construction() -> None:
    with pytest.raises(ValueError):
        CorsAllowlist.of(["*"])
    with pytest.raises(ValueError):
        CorsAllowlist.of(["https://*.example.com"])


# --------------------------------------------------------------- S172 token
def test_turn_token_round_trip() -> None:
    secret = secrets.token_bytes(32)
    clock = [1000]
    v = TurnTokenValidator(secret=secret, clock_ms=lambda: clock[0])
    ws, conv = uuid4(), uuid4()
    token = v.issue(workspace_id=ws, conversation_id=conv, ttl_ms=60_000)
    payload = v.verify(token)
    assert payload.workspace_id == ws
    assert payload.conversation_id == conv


def test_turn_token_rejects_tampered_signature() -> None:
    v = TurnTokenValidator(secret=b"x" * 32, clock_ms=lambda: 0)
    token = v.issue(
        workspace_id=uuid4(), conversation_id=uuid4(), ttl_ms=60_000
    )
    payload, sig = token.split(".")
    tampered = f"{payload}.{sig[:-1] + ('A' if sig[-1] != 'A' else 'B')}"
    with pytest.raises(TurnAuthError):
        v.verify(tampered)


def test_turn_token_rejects_expired() -> None:
    clock = [0]
    v = TurnTokenValidator(secret=b"y" * 32, clock_ms=lambda: clock[0])
    tok = v.issue(workspace_id=uuid4(), conversation_id=uuid4(), ttl_ms=1)
    clock[0] = 1000
    with pytest.raises(TurnAuthError):
        v.verify(tok)


def test_turn_token_validator_requires_min_secret() -> None:
    with pytest.raises(ValueError):
        TurnTokenValidator(secret=b"too-short")


# --------------------------------------------------------------- S174 guard
@pytest.mark.asyncio
async def test_guard_admits_valid_request() -> None:
    secret = b"z" * 32
    v = TurnTokenValidator(secret=secret, clock_ms=lambda: 0)
    cors = CorsAllowlist.of(["https://app"])
    limiter = RateLimiter(capacity=2, refill_per_sec=0, clock_ms=lambda: 0)
    guard = WebChannelGuard(cors=cors, tokens=v, limiter=limiter)
    tok = v.issue(workspace_id=uuid4(), conversation_id=uuid4())
    decision = await guard.admit(origin="https://app", token=tok)
    assert decision.allowed
    assert decision.reason == "ok"


@pytest.mark.asyncio
async def test_guard_blocks_disallowed_origin() -> None:
    v = TurnTokenValidator(secret=b"z" * 32)
    guard = WebChannelGuard(
        cors=CorsAllowlist.of(["https://app"]),
        tokens=v,
        limiter=RateLimiter(capacity=10, refill_per_sec=0, clock_ms=lambda: 0),
    )
    tok = v.issue(workspace_id=uuid4(), conversation_id=uuid4())
    decision = await guard.admit(origin="https://evil", token=tok)
    assert not decision.allowed
    assert decision.reason == "cors_blocked"


@pytest.mark.asyncio
async def test_guard_rate_limits_per_conversation() -> None:
    v = TurnTokenValidator(secret=b"z" * 32, clock_ms=lambda: 0)
    cors = CorsAllowlist.of(["https://app"])
    limiter = RateLimiter(capacity=1, refill_per_sec=0, clock_ms=lambda: 0)
    guard = WebChannelGuard(cors=cors, tokens=v, limiter=limiter)
    tok = v.issue(workspace_id=uuid4(), conversation_id=uuid4())
    assert (await guard.admit(origin="https://app", token=tok)).allowed
    second = await guard.admit(origin="https://app", token=tok)
    assert not second.allowed
    assert second.reason == "rate_limited"


@pytest.mark.asyncio
async def test_guard_reports_bad_token() -> None:
    v = TurnTokenValidator(secret=b"z" * 32)
    guard = WebChannelGuard(
        cors=CorsAllowlist.of(["https://app"]),
        tokens=v,
        limiter=RateLimiter(capacity=10, refill_per_sec=0, clock_ms=lambda: 0),
    )
    decision = await guard.admit(origin="https://app", token="garbage")  # noqa: S106
    assert not decision.allowed
    assert "token" in decision.reason or "malformed" in decision.reason
