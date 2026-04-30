"""``@tool``-decorated MCP surface for Zendesk Support."""

from __future__ import annotations

from loop_mcp import Tool, ToolRegistry, tool

from loop_mcp_zendesk.client import ZendeskClient, ZendeskError
from loop_mcp_zendesk.models import Comment, Ticket

_client: ZendeskClient | None = None


def bind_client(client: ZendeskClient) -> None:
    global _client
    _client = client


def _require_client() -> ZendeskClient:
    if _client is None:
        raise ZendeskError(
            "no Zendesk client bound; call bind_client() first"
        )
    return _client


@tool(name="zendesk_find_user")
async def find_user(email: str) -> dict[str, object] | None:
    """Find a Zendesk user by primary email."""
    user = await _require_client().find_user_by_email(email)
    return user.model_dump() if user else None


@tool(name="zendesk_get_ticket")
async def get_ticket(ticket_id: int) -> dict[str, object] | None:
    """Fetch a single ticket by id."""
    ticket = await _require_client().get_ticket(ticket_id)
    return ticket.model_dump() if ticket else None


@tool(name="zendesk_create_ticket")
async def create_ticket(
    subject: str,
    requester_id: int,
    description: str = "",
    priority: str = "normal",
    assignee_id: int | None = None,
    tags: list[str] | None = None,
) -> dict[str, object]:
    """Open a new Zendesk ticket on behalf of a requester."""
    ticket = Ticket(
        id=0,
        subject=subject,
        description=description,
        requester_id=requester_id,
        assignee_id=assignee_id,
        priority=priority,
        tags=tuple(tags or ()),
    )
    created = await _require_client().create_ticket(ticket)
    return created.model_dump()


@tool(name="zendesk_add_comment")
async def add_comment(
    ticket_id: int,
    author_id: int,
    body: str,
    public: bool = True,
) -> dict[str, object]:
    """Append a comment to an existing ticket."""
    comment = Comment(id=0, author_id=author_id, body=body, public=public)
    updated = await _require_client().add_comment(ticket_id, comment)
    return updated.model_dump()


def server_registry() -> ToolRegistry:
    """Return a :class:`ToolRegistry` populated with every Zendesk tool."""
    registry = ToolRegistry()
    for fn in (find_user, get_ticket, create_ticket, add_comment):
        descriptor: Tool = fn.__mcp_tool__  # type: ignore[attr-defined]
        registry.register(descriptor)
    return registry


__all__ = [
    "add_comment",
    "bind_client",
    "create_ticket",
    "find_user",
    "get_ticket",
    "server_registry",
]
