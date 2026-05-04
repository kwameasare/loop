"""Integration tests for :class:`PostgresRefreshTokenStore` [P0.2]."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from loop_control_plane.auth_exchange import (
    PostgresRefreshTokenStore,
    RefreshTokenRecord,
)
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

pytestmark = pytest.mark.integration


def _async_url(engine: Engine) -> str:
    """Render the password without masking — ``URL.__str__`` hides it."""
    return engine.url.render_as_string(hide_password=False)


@pytest_asyncio.fixture
async def refresh_store(
    migrated_postgres_engine: Engine,
) -> AsyncIterator[PostgresRefreshTokenStore]:
    with migrated_postgres_engine.begin() as conn:
        conn.execute(text("DELETE FROM refresh_tokens"))

    url = _async_url(migrated_postgres_engine)
    async_engine: AsyncEngine = create_async_engine(url)
    sync_engine: Engine = create_engine(url)
    try:
        yield PostgresRefreshTokenStore(async_engine, sync_engine)
    finally:
        await async_engine.dispose()
        sync_engine.dispose()


def _record(
    user_sub: str = "user-1",
    expires_at_ms: int = 10_000,
    family_id: str = "family-1",
    family_expires_at_ms: int = 20_000,
) -> dict[str, object]:
    return {
        "user_sub": user_sub,
        "expires_at_ms": expires_at_ms,
        "family_id": family_id,
        "family_expires_at_ms": family_expires_at_ms,
    }


@pytest.mark.asyncio
async def test_put_and_lookup_round_trip(
    refresh_store: PostgresRefreshTokenStore,
) -> None:
    await refresh_store.put(token_hash="hash-1", **_record())
    found = refresh_store.lookup("hash-1")
    assert found is not None
    assert found.user_sub == "user-1"
    assert found.expires_at_ms == 10_000
    assert found.family_id == "family-1"
    assert found.family_expires_at_ms == 20_000
    assert found.revoked_at_ms is None


@pytest.mark.asyncio
async def test_lookup_returns_none_for_unknown_token(
    refresh_store: PostgresRefreshTokenStore,
) -> None:
    assert refresh_store.lookup("never-issued") is None


@pytest.mark.asyncio
async def test_revoke_marks_record_with_revoked_at_ms(
    refresh_store: PostgresRefreshTokenStore,
) -> None:
    """The /v1/auth/refresh route distinguishes revoked-but-still-stored
    from never-existed: the former triggers family-wide revocation, the
    latter just 401s. The Postgres impl matches the in-memory soft-
    delete so the route's branching reads identically."""
    await refresh_store.put(token_hash="hash-1", **_record())
    await refresh_store.revoke("hash-1")
    found = refresh_store.lookup("hash-1")
    assert found is not None
    assert found.revoked_at_ms == 0


@pytest.mark.asyncio
async def test_revoke_unknown_token_is_noop(
    refresh_store: PostgresRefreshTokenStore,
) -> None:
    """Revoke must not raise on an unknown token — the route's
    expired-token branch revokes-then-returns-401 unconditionally."""
    await refresh_store.revoke("never-issued")  # must not raise


@pytest.mark.asyncio
async def test_revoke_already_revoked_token_is_noop(
    refresh_store: PostgresRefreshTokenStore,
) -> None:
    """Re-revoking a token must not bump revoked_at_ms — keeps a
    snapshot stable for callers comparing records."""
    await refresh_store.put(token_hash="hash-1", **_record())
    await refresh_store.revoke("hash-1")
    first = refresh_store.lookup("hash-1")
    await refresh_store.revoke("hash-1")
    second = refresh_store.lookup("hash-1")
    assert first == second


@pytest.mark.asyncio
async def test_revoke_family_marks_all_tokens_in_family(
    refresh_store: PostgresRefreshTokenStore,
) -> None:
    """Reuse-detection in the route depends on revoke_family killing
    every token sharing the family_id, not just the presented one."""
    await refresh_store.put(
        token_hash="hash-1", **_record(family_id="family-A")
    )
    await refresh_store.put(
        token_hash="hash-2", **_record(family_id="family-A")
    )
    await refresh_store.put(
        token_hash="hash-3", **_record(family_id="family-B")
    )
    await refresh_store.revoke_family("family-A")

    one = refresh_store.lookup("hash-1")
    two = refresh_store.lookup("hash-2")
    three = refresh_store.lookup("hash-3")
    assert one is not None and one.revoked_at_ms == 0
    assert two is not None and two.revoked_at_ms == 0
    # Family B untouched.
    assert three is not None and three.revoked_at_ms is None


@pytest.mark.asyncio
async def test_put_resets_revoked_state_on_conflict(
    refresh_store: PostgresRefreshTokenStore,
) -> None:
    """Token hashes are 32-byte random secrets so a real collision is
    astronomical. If it ever happened, ON CONFLICT DO UPDATE must
    re-issue cleanly (revoked_at_ms cleared) so the new token works
    even if the old one had been revoked."""
    await refresh_store.put(token_hash="hash-1", **_record())
    await refresh_store.revoke("hash-1")
    await refresh_store.put(
        token_hash="hash-1",
        user_sub="user-2",
        expires_at_ms=99_999,
        family_id="family-2",
        family_expires_at_ms=199_999,
    )
    found = refresh_store.lookup("hash-1")
    assert found == RefreshTokenRecord(
        user_sub="user-2",
        expires_at_ms=99_999,
        family_id="family-2",
        family_expires_at_ms=199_999,
        revoked_at_ms=None,
    )
