"""Tests for the first-party Zendesk MCP server (S047)."""

from __future__ import annotations

import pytest
from loop_mcp_zendesk import (
    InMemoryZendeskClient,
    Ticket,
    User,
    ZendeskConfig,
    ZendeskError,
    add_comment,
    create_ticket,
    find_user,
    get_ticket,
    server_registry,
)
from loop_mcp_zendesk import tools as zd_tools


@pytest.fixture
def client() -> InMemoryZendeskClient:
    users = (
        User(id=1, name="Ada", email="ada@acme.test", role="end-user"),
        User(id=2, name="Agent Smith", email="smith@acme.test", role="agent"),
    )
    tickets = (
        Ticket(
            id=100,
            subject="Cannot login",
            requester_id=1,
            assignee_id=2,
            status="open",
            priority="high",
        ),
    )
    return InMemoryZendeskClient(users=users, tickets=tickets)


@pytest.fixture(autouse=True)
def _bind(client: InMemoryZendeskClient) -> None:
    zd_tools.bind_client(client)


def test_config_base_url() -> None:
    cfg = ZendeskConfig(
        subdomain="loop",
        email="ops@loop.dev",
        api_token="t",
    )
    assert cfg.base_url == "https://loop.zendesk.com/api/v2"


def test_config_from_env() -> None:
    cfg = ZendeskConfig.from_env(
        {
            "ZD_SUBDOMAIN": "loop",
            "ZD_EMAIL": "ops@loop.dev",
            "ZD_API_TOKEN": "t",
        }
    )
    assert cfg.subdomain == "loop"


async def test_find_user_hit() -> None:
    result = await find_user(email="ada@acme.test")
    assert result is not None and result["id"] == 1


async def test_find_user_miss() -> None:
    assert await find_user(email="nobody@acme.test") is None


async def test_get_ticket_hit() -> None:
    result = await get_ticket(ticket_id=100)
    assert result is not None and result["subject"] == "Cannot login"


async def test_get_ticket_miss_returns_none() -> None:
    assert await get_ticket(ticket_id=9999) is None


async def test_create_ticket_assigns_id(
    client: InMemoryZendeskClient,
) -> None:
    created = await create_ticket(
        subject="Refund please",
        requester_id=1,
        description="Order 42",
        priority="urgent",
        tags=["billing", "vip"],
    )
    assert created["id"] > 100  # auto-incremented past the seed
    assert created["tags"] == ("billing", "vip")


async def test_create_ticket_unknown_requester_raises() -> None:
    with pytest.raises(ZendeskError):
        await create_ticket(subject="x", requester_id=999)


async def test_add_comment_appends() -> None:
    updated = await add_comment(
        ticket_id=100, author_id=2, body="On it.", public=True
    )
    assert len(updated["comments"]) == 1
    assert updated["comments"][0]["body"] == "On it."


async def test_add_comment_unknown_ticket_raises() -> None:
    with pytest.raises(ZendeskError):
        await add_comment(ticket_id=9999, author_id=1, body="x")


async def test_add_comment_unknown_author_raises() -> None:
    with pytest.raises(ZendeskError):
        await add_comment(ticket_id=100, author_id=999, body="x")


def test_server_registry_lists_all_tools() -> None:
    reg = server_registry()
    assert reg.names() == sorted(
        [
            "zendesk_add_comment",
            "zendesk_create_ticket",
            "zendesk_find_user",
            "zendesk_get_ticket",
        ]
    )


async def test_server_registry_call() -> None:
    reg = server_registry()
    out = await reg.call("zendesk_find_user", {"email": "ada@acme.test"})
    assert out is not None and out["id"] == 1
