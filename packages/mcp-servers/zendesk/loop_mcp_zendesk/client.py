"""Zendesk client Protocol and an in-memory test double."""

from __future__ import annotations

from itertools import count
from typing import Protocol, runtime_checkable

from loop_mcp_zendesk.models import Comment, Ticket, User


class ZendeskError(RuntimeError):
    """Raised for any client-side or remote failure."""


@runtime_checkable
class ZendeskClient(Protocol):
    async def find_user_by_email(self, email: str) -> User | None: ...

    async def get_ticket(self, ticket_id: int) -> Ticket | None: ...

    async def create_ticket(self, ticket: Ticket) -> Ticket: ...

    async def add_comment(
        self, ticket_id: int, comment: Comment
    ) -> Ticket: ...


class InMemoryZendeskClient:
    """Process-local fake."""

    def __init__(
        self,
        *,
        users: tuple[User, ...] = (),
        tickets: tuple[Ticket, ...] = (),
    ) -> None:
        self._users: dict[int, User] = {u.id: u for u in users}
        self._tickets: dict[int, Ticket] = {t.id: t for t in tickets}
        self._ticket_ids = count(start=max((*self._tickets, 0)) + 1)
        self._comment_ids = count(
            start=max(
                (c.id for t in tickets for c in t.comments), default=0
            )
            + 1
        )

    async def find_user_by_email(self, email: str) -> User | None:
        norm = email.strip().lower()
        for user in self._users.values():
            if (user.email or "").lower() == norm:
                return user
        return None

    async def get_ticket(self, ticket_id: int) -> Ticket | None:
        return self._tickets.get(ticket_id)

    async def create_ticket(self, ticket: Ticket) -> Ticket:
        if ticket.requester_id not in self._users:
            raise ZendeskError(
                f"unknown requester_id: {ticket.requester_id!r}"
            )
        new_id = ticket.id or next(self._ticket_ids)
        stored = ticket.model_copy(update={"id": new_id})
        self._tickets[new_id] = stored
        return stored

    async def add_comment(
        self, ticket_id: int, comment: Comment
    ) -> Ticket:
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            raise ZendeskError(f"unknown ticket_id: {ticket_id!r}")
        if comment.author_id not in self._users:
            raise ZendeskError(
                f"unknown author_id: {comment.author_id!r}"
            )
        new_id = comment.id or next(self._comment_ids)
        stored_comment = comment.model_copy(update={"id": new_id})
        updated = ticket.model_copy(
            update={"comments": (*ticket.comments, stored_comment)}
        )
        self._tickets[ticket_id] = updated
        return updated
