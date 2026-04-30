"""Salesforce client Protocol and an in-memory test double.

The production client (against api.salesforce.com REST v59.0) is
deliberately out of scope here -- the real adapter ships in S0xx
once OAuth refresh + rate-limit handling are nailed down. The tools
in this package depend only on the :class:`SalesforceClient`
Protocol so they can be unit-tested without network.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import uuid4

from loop_mcp_salesforce.models import Account, Case, Contact, Opportunity


class SalesforceError(RuntimeError):
    """Raised for any client-side or remote failure."""


@runtime_checkable
class SalesforceClient(Protocol):
    """Minimal CRM read/write surface used by the MCP tools."""

    async def find_account_by_name(self, name: str) -> Account | None: ...

    async def find_contact_by_email(self, email: str) -> Contact | None: ...

    async def create_case(self, case: Case) -> Case: ...

    async def list_open_opportunities(
        self, account_id: str
    ) -> tuple[Opportunity, ...]: ...


class InMemorySalesforceClient:
    """Process-local fake; suitable for tests, demos, and offline mode."""

    def __init__(
        self,
        *,
        accounts: tuple[Account, ...] = (),
        contacts: tuple[Contact, ...] = (),
        opportunities: tuple[Opportunity, ...] = (),
    ) -> None:
        self._accounts: dict[str, Account] = {a.id: a for a in accounts}
        self._contacts: dict[str, Contact] = {c.id: c for c in contacts}
        self._opportunities: dict[str, Opportunity] = {
            o.id: o for o in opportunities
        }
        self._cases: dict[str, Case] = {}

    async def find_account_by_name(self, name: str) -> Account | None:
        norm = name.strip().lower()
        for account in self._accounts.values():
            if account.name.lower() == norm:
                return account
        return None

    async def find_contact_by_email(self, email: str) -> Contact | None:
        norm = email.strip().lower()
        for contact in self._contacts.values():
            if (contact.email or "").lower() == norm:
                return contact
        return None

    async def create_case(self, case: Case) -> Case:
        if case.account_id not in self._accounts:
            raise SalesforceError(
                f"unknown account_id: {case.account_id!r}"
            )
        new_id = case.id or f"500{uuid4().hex[:15]}"
        stored = case.model_copy(update={"id": new_id})
        self._cases[stored.id] = stored
        return stored

    async def list_open_opportunities(
        self, account_id: str
    ) -> tuple[Opportunity, ...]:
        return tuple(
            o
            for o in self._opportunities.values()
            if o.account_id == account_id and not o.is_closed
        )

    # Test helpers --------------------------------------------------

    @property
    def cases(self) -> tuple[Case, ...]:
        return tuple(self._cases.values())
