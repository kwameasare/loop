"""Integration tests for :class:`PostgresApiKeyService` [P0.2]."""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from loop_control_plane.api_keys import (
    KEY_PREFIX,
    ApiKeyError,
    PostgresApiKeyService,
)
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

pytestmark = pytest.mark.integration


def _async_url(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def _seed_workspace(engine: Engine) -> UUID:
    ws_id = uuid4()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO workspaces (
                    id, name, slug, region, tenant_kms_key_id,
                    created_at, created_by
                ) VALUES (
                    :id, 'fixture', :slug, 'na-east',
                    'vault://transit/workspace/fixture', now(), 'fixture-user'
                )
                """
            ),
            {"id": ws_id, "slug": f"fixture-{ws_id.hex[:8]}"},
        )
    return ws_id


def _reset_tables(engine: Engine) -> None:
    """TRUNCATE workspaces CASCADE — clears api_keys via the FK
    cascade. Same superuser-required workaround as
    test_workspaces_postgres."""
    from sqlalchemy import create_engine

    admin_url = engine.url.set(username="test", password="test")
    admin_engine = create_engine(admin_url)
    try:
        with admin_engine.begin() as conn:
            conn.execute(
                text("TRUNCATE TABLE workspaces RESTART IDENTITY CASCADE")
            )
    finally:
        admin_engine.dispose()


@pytest_asyncio.fixture
async def api_key_service_with_workspace(
    migrated_postgres_engine: Engine,
) -> AsyncIterator[tuple[PostgresApiKeyService, UUID]]:
    _reset_tables(migrated_postgres_engine)
    workspace_id = _seed_workspace(migrated_postgres_engine)
    async_engine: AsyncEngine = create_async_engine(_async_url(migrated_postgres_engine))
    try:
        yield PostgresApiKeyService(async_engine), workspace_id
    finally:
        await async_engine.dispose()


@pytest.mark.asyncio
async def test_issue_returns_plaintext_with_correct_prefix(
    api_key_service_with_workspace: tuple[PostgresApiKeyService, UUID],
) -> None:
    svc, workspace_id = api_key_service_with_workspace
    issued = await svc.issue(
        workspace_id=workspace_id, name="ci", created_by="auth0|alice"
    )
    assert issued.plaintext.startswith(KEY_PREFIX)
    assert issued.record.workspace_id == workspace_id
    assert issued.record.name == "ci"
    assert issued.record.revoked_at is None


@pytest.mark.asyncio
async def test_verify_round_trips_plaintext_to_record(
    api_key_service_with_workspace: tuple[PostgresApiKeyService, UUID],
) -> None:
    svc, workspace_id = api_key_service_with_workspace
    issued = await svc.issue(
        workspace_id=workspace_id, name="ci", created_by="auth0|alice"
    )
    found = await svc.verify(issued.plaintext)
    assert found.id == issued.record.id
    assert found.workspace_id == workspace_id


@pytest.mark.asyncio
async def test_verify_rejects_invalid_format(
    api_key_service_with_workspace: tuple[PostgresApiKeyService, UUID],
) -> None:
    svc, _ = api_key_service_with_workspace
    with pytest.raises(ApiKeyError, match="invalid key format"):
        await svc.verify("not-a-loop-key")


@pytest.mark.asyncio
async def test_verify_rejects_unknown_prefix(
    api_key_service_with_workspace: tuple[PostgresApiKeyService, UUID],
) -> None:
    svc, _ = api_key_service_with_workspace
    with pytest.raises(ApiKeyError, match="unknown key"):
        await svc.verify(KEY_PREFIX + "x" * 32)


@pytest.mark.asyncio
async def test_verify_rejects_tampered_secret(
    api_key_service_with_workspace: tuple[PostgresApiKeyService, UUID],
) -> None:
    """Same prefix as a real key but a different tail past the
    prefix bytes — the hash compare must fail."""
    svc, workspace_id = api_key_service_with_workspace
    issued = await svc.issue(
        workspace_id=workspace_id, name="ci", created_by="auth0|alice"
    )
    # Replace everything after the prefix with zeros — the prefix
    # still matches but the secret is wrong.
    secret = issued.plaintext[len(KEY_PREFIX) :]
    prefix_chars = secret[:12]
    tampered = KEY_PREFIX + prefix_chars + "0" * (len(secret) - 12)
    with pytest.raises(ApiKeyError, match="bad secret"):
        await svc.verify(tampered)


@pytest.mark.asyncio
async def test_revoke_then_verify_rejects(
    api_key_service_with_workspace: tuple[PostgresApiKeyService, UUID],
) -> None:
    svc, workspace_id = api_key_service_with_workspace
    issued = await svc.issue(
        workspace_id=workspace_id, name="ci", created_by="auth0|alice"
    )
    revoked = await svc.revoke(key_id=issued.record.id)
    assert revoked.revoked_at is not None
    with pytest.raises(ApiKeyError, match="revoked"):
        await svc.verify(issued.plaintext)


@pytest.mark.asyncio
async def test_revoke_is_idempotent(
    api_key_service_with_workspace: tuple[PostgresApiKeyService, UUID],
) -> None:
    """Second revoke must return the same revoked_at — bumping it
    would be confusing for callers comparing snapshots."""
    svc, workspace_id = api_key_service_with_workspace
    issued = await svc.issue(
        workspace_id=workspace_id, name="ci", created_by="auth0|alice"
    )
    first = await svc.revoke(key_id=issued.record.id)
    second = await svc.revoke(key_id=issued.record.id)
    assert second.revoked_at == first.revoked_at


@pytest.mark.asyncio
async def test_revoke_unknown_key_raises(
    api_key_service_with_workspace: tuple[PostgresApiKeyService, UUID],
) -> None:
    svc, _ = api_key_service_with_workspace
    with pytest.raises(ApiKeyError, match="unknown key"):
        await svc.revoke(key_id=uuid4())


@pytest.mark.asyncio
async def test_list_for_workspace_scoped(
    migrated_postgres_engine: Engine,
    api_key_service_with_workspace: tuple[PostgresApiKeyService, UUID],
) -> None:
    svc, workspace_a = api_key_service_with_workspace
    workspace_b = _seed_workspace(migrated_postgres_engine)
    await svc.issue(workspace_id=workspace_a, name="a1", created_by="alice")
    await svc.issue(workspace_id=workspace_a, name="a2", created_by="alice")
    await svc.issue(workspace_id=workspace_b, name="b1", created_by="bob")
    in_a = await svc.list_for_workspace(workspace_a)
    in_b = await svc.list_for_workspace(workspace_b)
    assert len(in_a) == 2
    assert len(in_b) == 1
    assert {k.name for k in in_a} == {"a1", "a2"}


@pytest.mark.asyncio
async def test_list_for_workspace_includes_revoked_keys(
    api_key_service_with_workspace: tuple[PostgresApiKeyService, UUID],
) -> None:
    """list_for_workspace returns ALL keys (including revoked) so the
    UI can show a key history. Matches the in-memory contract — the
    in-memory ``self._by_id.values()`` returns everything."""
    svc, workspace_id = api_key_service_with_workspace
    a = await svc.issue(workspace_id=workspace_id, name="a", created_by="u")
    await svc.revoke(key_id=a.record.id)
    listed = await svc.list_for_workspace(workspace_id)
    assert len(listed) == 1
    assert listed[0].revoked_at is not None


@pytest.mark.asyncio
async def test_issue_in_unknown_workspace_raises(
    api_key_service_with_workspace: tuple[PostgresApiKeyService, UUID],
) -> None:
    """The api_keys.workspace_id FK rejects an issue against a
    non-existent workspace; we surface that as ApiKeyError."""
    svc, _ = api_key_service_with_workspace
    with pytest.raises(ApiKeyError):
        await svc.issue(
            workspace_id=uuid4(), name="ci", created_by="auth0|alice"
        )
