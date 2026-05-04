from __future__ import annotations

import time
from uuid import uuid4

import pytest
from loop_control_plane import (
    ApiKeyError,
    ApiKeyService,
    AuthError,
    HS256Verifier,
    Role,
    WorkspaceError,
    WorkspaceService,
    has_scope,
)

# ----------------------------------------------------------------- auth


def _verifier() -> HS256Verifier:
    return HS256Verifier(
        secret="dev-secret",
        issuer="https://test.auth0.com/",
        audience="https://api.loop.test",
    )


def test_hs256_round_trip() -> None:
    v = _verifier()
    now = int(time.time())
    token = v.sign(
        {
            "sub": "auth0|abc",
            "iss": "https://test.auth0.com/",
            "aud": "https://api.loop.test",
            "exp": now + 60,
            "iat": now,
            "scope": "workspace:write workspace:read",
        }
    )
    claims = v.verify(token)
    assert claims.sub == "auth0|abc"
    assert "workspace:write" in claims.scopes
    assert has_scope(claims, ["workspace:read"])


def test_hs256_rejects_tampered_signature() -> None:
    v = _verifier()
    token = v.sign(
        {
            "sub": "x",
            "iss": "https://test.auth0.com/",
            "aud": "https://api.loop.test",
            "exp": int(time.time()) + 60,
            "iat": int(time.time()),
        }
    )
    bad = token[:-2] + ("AA" if token[-2:] != "AA" else "BB")
    with pytest.raises(AuthError):
        v.verify(bad)


def test_hs256_rejects_wrong_audience() -> None:
    v = _verifier()
    token = v.sign(
        {
            "sub": "x",
            "iss": "https://test.auth0.com/",
            "aud": "https://other.example",
            "exp": int(time.time()) + 60,
            "iat": int(time.time()),
        }
    )
    with pytest.raises(AuthError):
        v.verify(token)


def test_hs256_rejects_expired() -> None:
    v = _verifier()
    token = v.sign(
        {
            "sub": "x",
            "iss": "https://test.auth0.com/",
            "aud": "https://api.loop.test",
            "exp": int(time.time()) - 3600,
            "iat": int(time.time()) - 7200,
        }
    )
    with pytest.raises(AuthError):
        v.verify(token)


# -------------------------------------------------------------- workspaces


@pytest.mark.asyncio
async def test_workspace_create_makes_owner_member() -> None:
    svc = WorkspaceService()
    ws = await svc.create(name="Team A", slug="team-a", owner_sub="auth0|alice")
    assert (await svc.role_of(workspace_id=ws.id, user_sub="auth0|alice")) is Role.OWNER
    listed = await svc.list_for_user("auth0|alice")
    assert [w.id for w in listed] == [ws.id]


@pytest.mark.asyncio
async def test_workspace_duplicate_slug_rejected() -> None:
    svc = WorkspaceService()
    await svc.create(name="A", slug="a", owner_sub="u1")
    with pytest.raises(WorkspaceError):
        await svc.create(name="A2", slug="a", owner_sub="u2")


@pytest.mark.asyncio
async def test_workspace_only_owner_can_delete() -> None:
    svc = WorkspaceService()
    ws = await svc.create(name="A", slug="a", owner_sub="u1")
    await svc.add_member(workspace_id=ws.id, user_sub="u2", role=Role.MEMBER)
    with pytest.raises(WorkspaceError):
        await svc.delete(workspace_id=ws.id, actor_sub="u2")
    await svc.delete(workspace_id=ws.id, actor_sub="u1")
    with pytest.raises(WorkspaceError):
        await svc.get(ws.id)


# ---------------------------------------------------------------- api keys


@pytest.mark.asyncio
async def test_api_key_issue_and_verify() -> None:
    svc = ApiKeyService()
    issued = await svc.issue(workspace_id=uuid4(), name="ci", created_by="auth0|alice")
    assert issued.plaintext.startswith("loop_sk_")
    record = await svc.verify(issued.plaintext)
    assert record.id == issued.record.id


@pytest.mark.asyncio
async def test_api_key_verify_rejects_revoked_and_garbage() -> None:
    svc = ApiKeyService()
    issued = await svc.issue(workspace_id=uuid4(), name="x", created_by="u")
    await svc.revoke(key_id=issued.record.id)
    with pytest.raises(ApiKeyError):
        await svc.verify(issued.plaintext)
    with pytest.raises(ApiKeyError):
        await svc.verify("not-a-key")


@pytest.mark.asyncio
async def test_api_key_list_scoped_to_workspace() -> None:
    svc = ApiKeyService()
    ws1, ws2 = uuid4(), uuid4()
    await svc.issue(workspace_id=ws1, name="a", created_by="u")
    await svc.issue(workspace_id=ws1, name="b", created_by="u")
    await svc.issue(workspace_id=ws2, name="c", created_by="u")
    assert len(await svc.list_for_workspace(ws1)) == 2
    assert len(await svc.list_for_workspace(ws2)) == 1
