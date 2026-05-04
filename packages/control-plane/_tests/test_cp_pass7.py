"""Tests for control-plane pass7 modules: healthz, auth_exchange, me_api."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

import pytest
from loop_control_plane.auth_exchange import (
    AuthExchange,
    AuthExchangeError,
    InMemoryRefreshTokenStore,
    UnknownIdpUser,
)
from loop_control_plane.healthz import build_healthz_payload
from loop_control_plane.jwks import JwtClaims
from loop_control_plane.me_api import MeAPI, UnknownUser, UserProfile
from loop_control_plane.workspaces import Role, WorkspaceService

# ----- healthz ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_healthz_all_green() -> None:
    info = await build_healthz_payload(
        version="1.0.0",
        commit_sha="abcdef1234",
        build_time="2026-05-26T04:00:00Z",
        db_probe=lambda: _async_true(),
        redis_probe=lambda: _async_true(),
        nats_probe=lambda: _async_true(),
    )
    assert info.status == "healthy"
    assert info.db_ok and info.redis_ok and info.nats_ok


@pytest.mark.asyncio
async def test_healthz_db_down_unhealthy() -> None:
    info = await build_healthz_payload(
        version="1.0.0",
        commit_sha="abcdef1234",
        build_time="t",
        db_probe=lambda: _async_false(),
    )
    assert info.status == "unhealthy"
    assert not info.db_ok


@pytest.mark.asyncio
async def test_healthz_redis_down_degraded() -> None:
    info = await build_healthz_payload(
        version="1.0.0",
        commit_sha="abcdef1234",
        build_time="t",
        redis_probe=lambda: _async_false(),
    )
    assert info.status == "degraded"


@pytest.mark.asyncio
async def test_healthz_probe_exception_returns_false() -> None:
    async def boom() -> bool:
        raise RuntimeError("network")

    info = await build_healthz_payload(
        version="1.0.0", commit_sha="abcdef1234", build_time="t", db_probe=boom
    )
    assert info.status == "unhealthy"


async def _async_true() -> bool:
    return True


async def _async_false() -> bool:
    return False


# ----- auth_exchange ---------------------------------------------------------


def _claims(sub: str = "auth0|user-1", aud: tuple[str, ...] = ("loop-cp",)) -> JwtClaims:
    return JwtClaims(
        sub=sub,
        iss="https://loop.us.auth0.com/",
        aud=aud,
        exp_ms=2_000_000_000_000,
        iat_ms=1_000_000_000_000,
        raw={"sub": sub},
    )


@pytest.mark.asyncio
async def test_auth_exchange_happy_path() -> None:
    store = InMemoryRefreshTokenStore()
    user_id = "11111111-1111-4111-8111-111111111111"

    async def mapper(sub: str) -> str | None:
        return user_id if sub == "auth0|user-1" else None

    ex = AuthExchange(
        paseto_key=b"\x00" * 32,
        refresh_store=store,
        user_mapper=mapper,
        expected_audience="loop-cp",
    )
    result = await ex.exchange(claims=_claims(), now_ms=1_700_000_000_000)
    assert result.access_token.startswith("v4.local.")
    assert len(result.refresh_token) > 30
    assert result.access_expires_at_ms > 1_700_000_000_000
    assert result.refresh_expires_at_ms > result.access_expires_at_ms
    refresh_hash = sha256(result.refresh_token.encode("ascii")).hexdigest()
    record = store.lookup(refresh_hash)
    assert record is not None
    assert record.family_id
    assert record.family_expires_at_ms == 1_700_000_000_000 + 90 * 24 * 60 * 60 * 1000


@pytest.mark.asyncio
async def test_auth_exchange_unknown_user() -> None:
    async def mapper(_sub: str) -> str | None:
        return None

    ex = AuthExchange(
        paseto_key=b"\x00" * 32,
        refresh_store=InMemoryRefreshTokenStore(),
        user_mapper=mapper,
        expected_audience="loop-cp",
    )
    with pytest.raises(UnknownIdpUser):
        await ex.exchange(claims=_claims(), now_ms=1_700_000_000_000)


@pytest.mark.asyncio
async def test_auth_exchange_audience_mismatch() -> None:
    async def mapper(_sub: str) -> str | None:
        return "uid"

    ex = AuthExchange(
        paseto_key=b"\x00" * 32,
        refresh_store=InMemoryRefreshTokenStore(),
        user_mapper=mapper,
        expected_audience="loop-cp",
    )
    with pytest.raises(AuthExchangeError):
        await ex.exchange(
            claims=_claims(aud=("not-loop",)), now_ms=1_700_000_000_000
        )


# ----- me_api ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_me_api_returns_workspaces_sorted() -> None:
    ws = WorkspaceService()
    await ws.create(name="Z Co", slug="zeta", owner_sub="u1")
    await ws.create(name="A Co", slug="alpha", owner_sub="u1")

    profile = UserProfile(
        sub="u1",
        email="u1@example.com",
        name="User One",
        created_at=datetime.now(UTC),
    )

    async def directory(sub: str) -> UserProfile | None:
        return profile if sub == "u1" else None

    api = MeAPI(workspace_service=ws, user_directory=directory)
    me = await api.get_me("u1")
    slugs = [w.slug for w in me.workspaces]
    assert slugs == ["alpha", "zeta"]
    assert me.workspaces[0].role == "owner"


@pytest.mark.asyncio
async def test_me_api_unknown_user_raises() -> None:
    async def directory(_sub: str) -> UserProfile | None:
        return None

    api = MeAPI(workspace_service=WorkspaceService(), user_directory=directory)
    with pytest.raises(UnknownUser):
        await api.get_me("ghost")


@pytest.mark.asyncio
async def test_me_api_to_dict_serialises() -> None:
    ws = WorkspaceService()
    await ws.create(name="A", slug="alpha", owner_sub="u1")
    await ws.add_member(workspace_id=(await ws.list_for_user("u1"))[0].id, user_sub="u2", role=Role.MEMBER)
    profile = UserProfile(
        sub="u2", email="u2@x.com", name="Two", created_at=datetime.now(UTC)
    )

    async def directory(_sub: str) -> UserProfile | None:
        return profile

    api = MeAPI(workspace_service=ws, user_directory=directory)
    payload = await api.to_dict("u2")
    assert payload["profile"]["sub"] == "u2"
    assert payload["workspaces"][0]["role"] == "member"


# avoid lint about unused uuid4 import
_unused = uuid4
