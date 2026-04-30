"""Stripe-flavored billing wire-up.

This is the *test* wiring used by the control plane. We intentionally do **not**
import ``stripe`` (the real SDK) here -- our cloud-portability rules forbid
binding to a vendor in a generic package. Instead we define a narrow
``StripeClient`` Protocol plus an ``InMemoryStripe`` test double. A real
deployment provides a thin adapter that fulfills the same Protocol and calls
``stripe-python`` from a separate module that lives outside this package.

Public surface:

* ``StripeClient`` (Protocol) -- minimum subset of Stripe we depend on
  (customers + usage records + invoice draft).
* ``InMemoryStripe`` -- in-process implementation suitable for tests and
  local docker-compose.
* ``BillingError`` -- raised on attempts to bill a workspace that has no
  customer attached.
* ``BillingService`` -- high-level API the control plane uses:
  ``ensure_customer``, ``record_usage``, ``draft_invoice``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class BillingError(RuntimeError):
    """Raised when a billing operation cannot proceed."""


class StripeCustomer(BaseModel):
    """A workspace's billing customer record."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    id: str = Field(min_length=1)
    workspace_id: UUID
    email: str = Field(min_length=1)


class StripeUsageRecord(BaseModel):
    """A unit of metered usage attached to a customer."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    quantity: int = Field(ge=0)
    timestamp_ms: int = Field(ge=0)


class StripeInvoice(BaseModel):
    """A draft invoice that aggregates usage for a billing period."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    period_start_ms: int = Field(ge=0)
    period_end_ms: int = Field(ge=0)
    line_items: tuple[tuple[str, int], ...] = Field(default_factory=tuple)
    amount_cents: int = Field(ge=0)


class StripeClient(Protocol):
    """Narrow subset of Stripe we depend on."""

    async def create_customer(self, *, workspace_id: UUID, email: str) -> StripeCustomer: ...

    async def record_usage(
        self,
        *,
        customer_id: str,
        metric: str,
        quantity: int,
        timestamp_ms: int,
    ) -> StripeUsageRecord: ...

    async def draft_invoice(
        self,
        *,
        customer_id: str,
        period_start_ms: int,
        period_end_ms: int,
        rates_cents_per_unit: dict[str, int],
    ) -> StripeInvoice: ...


@dataclass
class InMemoryStripe:
    """Test double satisfying ``StripeClient``."""

    customers: dict[str, StripeCustomer] = field(default_factory=dict)
    by_workspace: dict[UUID, str] = field(default_factory=dict)
    usage: list[StripeUsageRecord] = field(default_factory=list)
    invoices: dict[str, StripeInvoice] = field(default_factory=dict)

    async def create_customer(self, *, workspace_id: UUID, email: str) -> StripeCustomer:
        existing = self.by_workspace.get(workspace_id)
        if existing is not None:
            return self.customers[existing]
        cid = f"cus_{uuid4().hex[:14]}"
        cust = StripeCustomer(id=cid, workspace_id=workspace_id, email=email)
        self.customers[cid] = cust
        self.by_workspace[workspace_id] = cid
        return cust

    async def record_usage(
        self,
        *,
        customer_id: str,
        metric: str,
        quantity: int,
        timestamp_ms: int,
    ) -> StripeUsageRecord:
        if customer_id not in self.customers:
            raise BillingError(f"unknown customer: {customer_id}")
        rec = StripeUsageRecord(
            id=f"mbur_{uuid4().hex[:14]}",
            customer_id=customer_id,
            metric=metric,
            quantity=quantity,
            timestamp_ms=timestamp_ms,
        )
        self.usage.append(rec)
        return rec

    async def draft_invoice(
        self,
        *,
        customer_id: str,
        period_start_ms: int,
        period_end_ms: int,
        rates_cents_per_unit: dict[str, int],
    ) -> StripeInvoice:
        if customer_id not in self.customers:
            raise BillingError(f"unknown customer: {customer_id}")
        if period_end_ms < period_start_ms:
            raise BillingError("period_end before period_start")
        per_metric: dict[str, int] = {}
        for rec in self.usage:
            if rec.customer_id != customer_id:
                continue
            if not period_start_ms <= rec.timestamp_ms < period_end_ms:
                continue
            per_metric[rec.metric] = per_metric.get(rec.metric, 0) + rec.quantity
        amount = 0
        items: list[tuple[str, int]] = []
        for metric, qty in sorted(per_metric.items()):
            rate = rates_cents_per_unit.get(metric, 0)
            line_cents = rate * qty
            amount += line_cents
            items.append((metric, line_cents))
        inv = StripeInvoice(
            id=f"in_{uuid4().hex[:14]}",
            customer_id=customer_id,
            period_start_ms=period_start_ms,
            period_end_ms=period_end_ms,
            line_items=tuple(items),
            amount_cents=amount,
        )
        self.invoices[inv.id] = inv
        return inv


@dataclass
class BillingService:
    """High-level billing API used by the control plane."""

    client: StripeClient
    rates_cents_per_unit: dict[str, int] = field(default_factory=dict)
    _by_workspace: dict[UUID, str] = field(default_factory=dict)

    async def ensure_customer(self, *, workspace_id: UUID, email: str) -> StripeCustomer:
        existing = self._by_workspace.get(workspace_id)
        if existing is not None and isinstance(self.client, InMemoryStripe):
            return self.client.customers[existing]
        cust = await self.client.create_customer(workspace_id=workspace_id, email=email)
        self._by_workspace[workspace_id] = cust.id
        return cust

    async def record_usage(
        self,
        *,
        workspace_id: UUID,
        metric: str,
        quantity: int,
        timestamp_ms: int,
    ) -> StripeUsageRecord:
        if quantity < 0:
            raise BillingError("quantity must be non-negative")
        cid = self._by_workspace.get(workspace_id)
        if cid is None:
            raise BillingError(
                f"workspace {workspace_id} has no customer; call ensure_customer first"
            )
        return await self.client.record_usage(
            customer_id=cid,
            metric=metric,
            quantity=quantity,
            timestamp_ms=timestamp_ms,
        )

    async def draft_invoice(
        self,
        *,
        workspace_id: UUID,
        period_start_ms: int,
        period_end_ms: int,
    ) -> StripeInvoice:
        cid = self._by_workspace.get(workspace_id)
        if cid is None:
            raise BillingError(
                f"workspace {workspace_id} has no customer; call ensure_customer first"
            )
        return await self.client.draft_invoice(
            customer_id=cid,
            period_start_ms=period_start_ms,
            period_end_ms=period_end_ms,
            rates_cents_per_unit=dict(self.rates_cents_per_unit),
        )


__all__ = [
    "BillingError",
    "BillingService",
    "InMemoryStripe",
    "StripeClient",
    "StripeCustomer",
    "StripeInvoice",
    "StripeUsageRecord",
]
