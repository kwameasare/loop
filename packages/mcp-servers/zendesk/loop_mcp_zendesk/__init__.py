"""First-party Loop MCP server for Zendesk Support."""

from loop_mcp_zendesk.client import (
    InMemoryZendeskClient,
    ZendeskClient,
    ZendeskError,
)
from loop_mcp_zendesk.config import ZendeskConfig
from loop_mcp_zendesk.models import Comment, Ticket, User
from loop_mcp_zendesk.tools import (
    add_comment,
    create_ticket,
    find_user,
    get_ticket,
    server_registry,
)

__all__ = [
    "Comment",
    "InMemoryZendeskClient",
    "Ticket",
    "User",
    "ZendeskClient",
    "ZendeskConfig",
    "ZendeskError",
    "add_comment",
    "create_ticket",
    "find_user",
    "get_ticket",
    "server_registry",
]
