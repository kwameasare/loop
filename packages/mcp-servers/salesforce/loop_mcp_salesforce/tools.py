"""``@tool``-decorated MCP surface for Salesforce.

The tools take a :class:`SalesforceClient` via a module-level binding
so the registry exposes plain ``inputSchema``-shaped functions to the
MCP wire protocol. Use :func:`bind_client` in tests or in the server
bootstrap to swap in a concrete client.
"""

from __future__ import annotations

from loop_mcp import Tool, ToolRegistry, tool

from loop_mcp_salesforce.client import (
    InMemorySalesforceClient,
    SalesforceClient,
    SalesforceError,
)
from loop_mcp_salesforce.models import Account, Case, Contact, Opportunity

_client: SalesforceClient | None = None


def bind_client(client: SalesforceClient) -> None:
    """Bind a concrete :class:`SalesforceClient` for the tool calls."""
    global _client
    _client = client


def _require_client() -> SalesforceClient:
    if _client is None:
        raise SalesforceError(
            "no Salesforce client bound; call bind_client() first"
        )
    return _client


@tool(name="salesforce_find_account")
async def find_account(name: str) -> dict[str, object] | None:
    """Find a Salesforce Account by exact (case-insensitive) name.

    Returns ``None`` when no match exists.
    """
    account = await _require_client().find_account_by_name(name)
    return account.model_dump() if account else None


@tool(name="salesforce_find_contact")
async def find_contact(email: str) -> dict[str, object] | None:
    """Find a Salesforce Contact by primary email."""
    contact = await _require_client().find_contact_by_email(email)
    return contact.model_dump() if contact else None


@tool(name="salesforce_create_case")
async def create_case(
    account_id: str,
    subject: str,
    description: str = "",
    priority: str = "Medium",
    contact_id: str | None = None,
) -> dict[str, object]:
    """Open a new support Case on the given Account.

    Returns the created Case (including the newly assigned id).
    """
    case = Case(
        id="",
        account_id=account_id,
        contact_id=contact_id,
        subject=subject,
        description=description,
        priority=priority,
    )
    created = await _require_client().create_case(case)
    return created.model_dump()


@tool(name="salesforce_list_open_opportunities")
async def list_open_opportunities(account_id: str) -> list[dict[str, object]]:
    """List every open Opportunity for an Account."""
    opps = await _require_client().list_open_opportunities(account_id)
    return [o.model_dump() for o in opps]


def server_registry() -> ToolRegistry:
    """Return a :class:`ToolRegistry` populated with every Salesforce tool."""
    registry = ToolRegistry()
    for fn in (find_account, find_contact, create_case, list_open_opportunities):
        descriptor: Tool = fn.__mcp_tool__  # type: ignore[attr-defined]
        registry.register(descriptor)
    return registry


__all__ = [
    "Account",
    "Case",
    "Contact",
    "InMemorySalesforceClient",
    "Opportunity",
    "bind_client",
    "create_case",
    "find_account",
    "find_contact",
    "list_open_opportunities",
    "server_registry",
]
