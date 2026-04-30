"""``agent_phone_numbers`` provisioning (S382, extends S049).

A workspace can *bring its own* Twilio/Telnyx number and hand it to
Loop. We track ownership in this in-memory store (control-plane wires
the same shape against Postgres). The store enforces:

* E.164 numbers only (anchored regex; no extensions)
* Globally unique \u2014 a number can be claimed by at most one workspace
* Soft-delete on release (``released_at`` set, row preserved for audit)
* Re-claim of a previously-released number is allowed and bumps the
  ``claimed_at`` while clearing ``released_at``.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

_E164 = re.compile(r"^\+[1-9]\d{6,14}$")


class ProvisioningStatus(StrEnum):
    ACTIVE = "active"
    RELEASED = "released"


class PhoneProvisioningError(RuntimeError):
    """Generic provisioning failure (validation / conflict)."""


class PhoneNumberRecord(BaseModel):
    """One row in the ``agent_phone_numbers`` table."""

    model_config = ConfigDict(extra="forbid", frozen=False, strict=True)

    e164: str = Field(min_length=4, max_length=16)
    workspace_id: UUID
    carrier: str = Field(min_length=1, max_length=64)
    claimed_at: datetime
    released_at: datetime | None = None
    status: ProvisioningStatus = ProvisioningStatus.ACTIVE


def _validate_e164(value: str) -> str:
    if not _E164.match(value):
        raise PhoneProvisioningError(f"{value!r} is not a valid E.164 number")
    return value


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


class PhoneNumberStore:
    """In-process store for the ``agent_phone_numbers`` table."""

    def __init__(self) -> None:
        self._rows: dict[str, PhoneNumberRecord] = {}

    def claim(
        self,
        *,
        e164: str,
        workspace_id: UUID,
        carrier: str,
        now: datetime | None = None,
    ) -> PhoneNumberRecord:
        e164 = _validate_e164(e164)
        existing = self._rows.get(e164)
        ts = now or _utcnow()
        if existing is not None:
            if existing.status is ProvisioningStatus.ACTIVE:
                raise PhoneProvisioningError(
                    f"{e164} already claimed by workspace {existing.workspace_id}"
                )
            # Re-claim of a previously-released number.
            existing.workspace_id = workspace_id
            existing.carrier = carrier
            existing.claimed_at = ts
            existing.released_at = None
            existing.status = ProvisioningStatus.ACTIVE
            return existing
        record = PhoneNumberRecord(
            e164=e164,
            workspace_id=workspace_id,
            carrier=carrier,
            claimed_at=ts,
        )
        self._rows[e164] = record
        return record

    def release(
        self,
        *,
        e164: str,
        workspace_id: UUID,
        now: datetime | None = None,
    ) -> PhoneNumberRecord:
        e164 = _validate_e164(e164)
        record = self._rows.get(e164)
        if record is None or record.status is ProvisioningStatus.RELEASED:
            raise PhoneProvisioningError(f"{e164} is not claimed")
        if record.workspace_id != workspace_id:
            raise PhoneProvisioningError(
                f"{e164} is owned by a different workspace"
            )
        record.released_at = now or _utcnow()
        record.status = ProvisioningStatus.RELEASED
        return record

    def list_active(self, workspace_id: UUID) -> list[PhoneNumberRecord]:
        return sorted(
            (
                r
                for r in self._rows.values()
                if r.workspace_id == workspace_id
                and r.status is ProvisioningStatus.ACTIVE
            ),
            key=lambda r: r.e164,
        )

    def get(self, e164: str) -> PhoneNumberRecord:
        e164 = _validate_e164(e164)
        try:
            return self._rows[e164]
        except KeyError as exc:
            raise PhoneProvisioningError(f"{e164} not found") from exc


__all__ = [
    "PhoneNumberRecord",
    "PhoneNumberStore",
    "PhoneProvisioningError",
    "ProvisioningStatus",
]
