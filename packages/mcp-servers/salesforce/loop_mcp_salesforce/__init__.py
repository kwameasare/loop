"""First-party Loop MCP server for Salesforce.

This package exposes a small, opinionated set of CRM operations as
``@tool``-decorated functions backed by an injectable HTTP client.
The HTTP layer is a Protocol so unit tests can stub it; in production
the client wraps salesforce.com REST API v59.0 endpoints.

Why first-party? Because the long tail of community Salesforce MCP
servers each model fields slightly differently. Loop picks one shape
(strict pydantic) and supports it as part of the platform contract.

Public surface:

* :class:`SalesforceConfig` -- env-driven config.
* :class:`SalesforceClient` Protocol + :class:`InMemorySalesforceClient`
  for tests and demos.
* The tool functions: ``find_account``, ``find_contact``,
  ``create_case``, ``list_open_opportunities``.
* :func:`server_registry` -- a :class:`loop_mcp.ToolRegistry` populated
  with every tool, ready to be served by ``loop-cli mcp serve``.
"""

from loop_mcp_salesforce.client import (
    InMemorySalesforceClient,
    SalesforceClient,
    SalesforceError,
)
from loop_mcp_salesforce.config import SalesforceConfig
from loop_mcp_salesforce.models import (
    Account,
    Case,
    Contact,
    Opportunity,
)
from loop_mcp_salesforce.tools import (
    create_case,
    find_account,
    find_contact,
    list_open_opportunities,
    server_registry,
)

__all__ = [
    "Account",
    "Case",
    "Contact",
    "InMemorySalesforceClient",
    "Opportunity",
    "SalesforceClient",
    "SalesforceConfig",
    "SalesforceError",
    "create_case",
    "find_account",
    "find_contact",
    "list_open_opportunities",
    "server_registry",
]
