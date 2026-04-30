"""Phone number lifecycle at the Loop layer.

Loop sits in front of N upstream telephony providers (Twilio, Telnyx,
Vonage, Bandwidth). To agent authors we expose **one** namespace of
phone numbers regardless of which carrier actually owns the SIP
trunk. This module models the search → buy → assign → release →
port lifecycle and the ``PhoneNumberProvisioner`` Protocol every
carrier adapter must satisfy.

The shipped :class:`InMemoryPhoneNumberProvisioner` is the test
double; real adapters live under
``loop_voice.phone.adapters.{twilio,telnyx,...}`` (filed under
S049b).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


_E164 = re.compile(r"^\+[1-9]\d{6,14}$")


class PhoneCapability(StrEnum):
    VOICE = "voice"
    SMS = "sms"
    MMS = "mms"
    FAX = "fax"


class PhoneNumberStatus(StrEnum):
    """Lifecycle states for a Loop-managed phone number."""

    AVAILABLE = "available"  # in carrier inventory, not yet bought
    PROVISIONING = "provisioning"  # buy in flight
    ACTIVE = "active"  # bought and assigned
    RELEASING = "releasing"  # release in flight
    RELEASED = "released"  # returned to carrier
    PORTING_OUT = "porting_out"  # port-out in flight


class PhoneNumberSearchQuery(_StrictModel):
    country: str = Field(min_length=2, max_length=2)
    area_code: str | None = None
    contains: str | None = None
    capabilities: tuple[PhoneCapability, ...] = (PhoneCapability.VOICE,)
    limit: int = Field(default=10, ge=1, le=100)


class PhoneNumberCandidate(_StrictModel):
    """A number offered by an upstream carrier, not yet bought."""

    e164: str
    country: str = Field(min_length=2, max_length=2)
    carrier: str = Field(min_length=1)
    capabilities: tuple[PhoneCapability, ...]
    monthly_cost_usd: float = Field(ge=0)


class PhoneNumber(_StrictModel):
    """A Loop-owned number bound to a tenant agent."""

    id: str = Field(min_length=1)
    e164: str
    country: str = Field(min_length=2, max_length=2)
    carrier: str = Field(min_length=1)
    capabilities: tuple[PhoneCapability, ...]
    status: PhoneNumberStatus
    tenant_id: str = Field(min_length=1)
    agent_id: str | None = None
    acquired_at: datetime
    released_at: datetime | None = None


class PhoneProvisioningError(Exception):
    """Raised by adapters on carrier or policy failure."""


def validate_e164(number: str) -> str:
    """Return ``number`` if it parses as E.164; otherwise raise."""
    if not _E164.match(number):
        raise PhoneProvisioningError(
            f"not a valid E.164 number: {number!r}"
        )
    return number


class PhoneNumberProvisioner(Protocol):
    """Carrier-agnostic provisioning surface.

    Implementations must be safe to call from async runtime code.
    """

    async def search(
        self, query: PhoneNumberSearchQuery
    ) -> Sequence[PhoneNumberCandidate]: ...

    async def buy(
        self,
        candidate: PhoneNumberCandidate,
        *,
        tenant_id: str,
        agent_id: str | None = None,
    ) -> PhoneNumber: ...

    async def assign(
        self, number_id: str, *, agent_id: str
    ) -> PhoneNumber: ...

    async def release(self, number_id: str) -> PhoneNumber: ...

    async def list_active(
        self, tenant_id: str
    ) -> Sequence[PhoneNumber]: ...


class InMemoryPhoneNumberProvisioner:
    """In-memory test double for :class:`PhoneNumberProvisioner`."""

    def __init__(
        self,
        *,
        inventory: Iterable[PhoneNumberCandidate] = (),
        clock: object | None = None,
    ) -> None:
        self._inventory: list[PhoneNumberCandidate] = list(inventory)
        self._owned: dict[str, PhoneNumber] = {}
        self._next_id = 1
        # clock kept as object-typed hook so tests can inject a fake;
        # default is real UTC now.
        self._clock = clock

    def _now(self) -> datetime:
        if self._clock is not None:
            return self._clock()  # type: ignore[no-any-return,operator]
        return datetime.now(UTC)

    async def search(
        self, query: PhoneNumberSearchQuery
    ) -> Sequence[PhoneNumberCandidate]:
        out: list[PhoneNumberCandidate] = []
        for c in self._inventory:
            if c.country.upper() != query.country.upper():
                continue
            if query.area_code and not c.e164[2:].startswith(
                query.area_code
            ):
                continue
            if query.contains and query.contains not in c.e164:
                continue
            if not all(cap in c.capabilities for cap in query.capabilities):
                continue
            out.append(c)
            if len(out) >= query.limit:
                break
        return tuple(out)

    async def buy(
        self,
        candidate: PhoneNumberCandidate,
        *,
        tenant_id: str,
        agent_id: str | None = None,
    ) -> PhoneNumber:
        validate_e164(candidate.e164)
        if any(
            n.e164 == candidate.e164
            and n.status
            in (
                PhoneNumberStatus.ACTIVE,
                PhoneNumberStatus.PROVISIONING,
            )
            for n in self._owned.values()
        ):
            raise PhoneProvisioningError(
                f"{candidate.e164} already owned by Loop"
            )
        if candidate not in self._inventory:
            raise PhoneProvisioningError(
                f"{candidate.e164} not in carrier inventory"
            )
        number_id = f"pn_{self._next_id:06d}"
        self._next_id += 1
        number = PhoneNumber(
            id=number_id,
            e164=candidate.e164,
            country=candidate.country,
            carrier=candidate.carrier,
            capabilities=candidate.capabilities,
            status=PhoneNumberStatus.ACTIVE,
            tenant_id=tenant_id,
            agent_id=agent_id,
            acquired_at=self._now(),
            released_at=None,
        )
        self._owned[number_id] = number
        self._inventory.remove(candidate)
        return number

    async def assign(
        self, number_id: str, *, agent_id: str
    ) -> PhoneNumber:
        existing = self._owned.get(number_id)
        if existing is None:
            raise PhoneProvisioningError(f"unknown number {number_id!r}")
        if existing.status != PhoneNumberStatus.ACTIVE:
            raise PhoneProvisioningError(
                f"{number_id} is {existing.status}, cannot reassign"
            )
        updated = existing.model_copy(update={"agent_id": agent_id})
        self._owned[number_id] = updated
        return updated

    async def release(self, number_id: str) -> PhoneNumber:
        existing = self._owned.get(number_id)
        if existing is None:
            raise PhoneProvisioningError(f"unknown number {number_id!r}")
        if existing.status == PhoneNumberStatus.RELEASED:
            raise PhoneProvisioningError(
                f"{number_id} is already released"
            )
        updated = existing.model_copy(
            update={
                "status": PhoneNumberStatus.RELEASED,
                "agent_id": None,
                "released_at": self._now(),
            }
        )
        self._owned[number_id] = updated
        return updated

    async def list_active(
        self, tenant_id: str
    ) -> Sequence[PhoneNumber]:
        return tuple(
            n
            for n in self._owned.values()
            if n.tenant_id == tenant_id
            and n.status == PhoneNumberStatus.ACTIVE
        )


__all__ = [
    "InMemoryPhoneNumberProvisioner",
    "PhoneCapability",
    "PhoneNumber",
    "PhoneNumberCandidate",
    "PhoneNumberProvisioner",
    "PhoneNumberSearchQuery",
    "PhoneNumberStatus",
    "PhoneProvisioningError",
    "validate_e164",
]
