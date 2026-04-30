"""Tests for the first-party Salesforce MCP server (S047)."""

from __future__ import annotations

import asyncio

import pytest
from loop_mcp_salesforce import (
    Account,
    Contact,
    InMemorySalesforceClient,
    Opportunity,
    SalesforceConfig,
    SalesforceError,
    create_case,
    find_account,
    find_contact,
    list_open_opportunities,
    server_registry,
)
from loop_mcp_salesforce import tools as sf_tools


@pytest.fixture
def client() -> InMemorySalesforceClient:
    accounts = (
        Account(id="001A", name="Acme Inc", industry="Manufacturing"),
        Account(id="001B", name="Globex"),
    )
    contacts = (
        Contact(id="003A", account_id="001A", name="Ada", email="ada@acme.test"),
    )
    opportunities = (
        Opportunity(id="006A", account_id="001A", name="Renewal Q3",
                    stage="Negotiation", amount=50_000.0),
        Opportunity(id="006B", account_id="001A", name="Closed-Won",
                    stage="Closed Won", is_closed=True, is_won=True),
    )
    return InMemorySalesforceClient(
        accounts=accounts, contacts=contacts, opportunities=opportunities
    )


@pytest.fixture(autouse=True)
def _bind(client: InMemorySalesforceClient) -> None:
    sf_tools.bind_client(client)


def test_config_from_env_reads_required_keys() -> None:
    cfg = SalesforceConfig.from_env(
        {
            "SF_INSTANCE_URL": "https://acme.my.salesforce.com",
            "SF_CLIENT_ID": "cid",
            "SF_CLIENT_SECRET": "sec",
            "SF_REFRESH_TOKEN": "tok",
        }
    )
    assert cfg.instance_url == "https://acme.my.salesforce.com"
    assert cfg.api_version == "v59.0"


def test_config_missing_key_raises() -> None:
    with pytest.raises(KeyError):
        SalesforceConfig.from_env({"SF_INSTANCE_URL": "x"})


async def test_find_account_hit() -> None:
    result = await find_account(name="Acme Inc")
    assert result is not None
    assert result["id"] == "001A"


async def test_find_account_case_insensitive() -> None:
    result = await find_account(name="acme inc")
    assert result is not None and result["id"] == "001A"


async def test_find_account_miss_returns_none() -> None:
    assert await find_account(name="nope") is None


async def test_find_contact_by_email() -> None:
    result = await find_contact(email="ada@acme.test")
    assert result is not None and result["id"] == "003A"


async def test_create_case_assigns_id_and_persists(
    client: InMemorySalesforceClient,
) -> None:
    created = await create_case(
        account_id="001A",
        subject="Login broken",
        description="Cannot reset password",
        priority="High",
    )
    assert created["id"]
    assert created["subject"] == "Login broken"
    assert len(client.cases) == 1


async def test_create_case_unknown_account_raises() -> None:
    with pytest.raises(SalesforceError):
        await create_case(account_id="missing", subject="x")


async def test_list_open_opportunities_excludes_closed() -> None:
    result = await list_open_opportunities(account_id="001A")
    assert len(result) == 1
    assert result[0]["id"] == "006A"


def test_server_registry_describes_all_tools() -> None:
    reg = server_registry()
    names = reg.names()
    assert names == sorted(
        [
            "salesforce_create_case",
            "salesforce_find_account",
            "salesforce_find_contact",
            "salesforce_list_open_opportunities",
        ]
    )
    for d in reg.describe_all():
        assert d["inputSchema"]["type"] == "object"


async def test_server_registry_call_routes_to_tool() -> None:
    reg = server_registry()
    out = await reg.call("salesforce_find_account", {"name": "Acme Inc"})
    assert out is not None and out["id"] == "001A"


def test_unbound_client_raises() -> None:
    sf_tools._client = None
    with pytest.raises(SalesforceError):
        asyncio.run(find_account(name="x"))


def test_in_memory_client_implements_protocol(
    client: InMemorySalesforceClient,
) -> None:
    from loop_mcp_salesforce.client import SalesforceClient

    assert isinstance(client, SalesforceClient)
