"""Workspace member invite service (S111).

Flow:
1. Admin issues an invite for ``email`` at ``role`` for a given workspace.
2. ``Invite.token`` is a stable opaque secret returned once at issuance and
   stored only as a sha256 hash on the service. Treat like an API key.
3. Recipient calls ``accept`` with the token + their identity sub. We verify
   the hash, check expiry, then add a Membership.

The service is async + in-memory. A clock_ms callable is injectable for
deterministic tests of expiry semantics.
"""

from __future__ import annotations

import asyncio
import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane.workspaces import Membership, Role, WorkspaceService

DEFAULT_TTL_MS = 7 * 24 * 60 * 60 * 1000  # one week


__all__ = [
    "Invite",
    "InviteError",
    "InviteService",
    "IssuedInvite",
]


class InviteError(ValueError):
    """Raised on duplicate, expired, unknown, or already-consumed invites."""


class Invite(BaseModel):
    """Public-safe view of an invite (no token plaintext)."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: UUID
    workspace_id: UUID
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    role: Role
    invited_by: str = Field(min_length=1)
    expires_at_ms: int = Field(ge=0)
    accepted: bool = False


class IssuedInvite(BaseModel):
    """Returned exactly once at creation; carries the plaintext token."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    invite: Invite
    token: str = Field(min_length=32)


def _hash_token(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


@dataclass
class InviteService:
    """Issue + accept workspace invites."""

    workspaces: WorkspaceService
    ttl_ms: int = DEFAULT_TTL_MS
    clock_ms: Callable[[], int] = field(default_factory=lambda: lambda: 0)
    _by_id: dict[UUID, Invite] = field(default_factory=dict)
    _hash_to_id: dict[str, UUID] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def issue(
        self,
        *,
        workspace_id: UUID,
        email: str,
        role: Role,
        invited_by: str,
    ) -> IssuedInvite:
        async with self._lock:
            for existing in self._by_id.values():
                if (
                    existing.workspace_id == workspace_id
                    and existing.email == email
                    and not existing.accepted
                    and existing.expires_at_ms > self.clock_ms()
                ):
                    raise InviteError(
                        f"already invited: {email} (workspace={workspace_id})"
                    )
            token = secrets.token_urlsafe(32)
            invite = Invite(
                id=uuid4(),
                workspace_id=workspace_id,
                email=email,
                role=role,
                invited_by=invited_by,
                expires_at_ms=self.clock_ms() + self.ttl_ms,
            )
            self._by_id[invite.id] = invite
            self._hash_to_id[_hash_token(token)] = invite.id
            return IssuedInvite(invite=invite, token=token)

    async def accept(self, *, token: str, user_sub: str) -> Membership:
        async with self._lock:
            invite_id = self._hash_to_id.get(_hash_token(token))
            if invite_id is None:
                raise InviteError("unknown invite token")
            invite = self._by_id[invite_id]
            if invite.accepted:
                raise InviteError("invite already accepted")
            if invite.expires_at_ms <= self.clock_ms():
                raise InviteError("invite expired")
            self._by_id[invite_id] = invite.model_copy(update={"accepted": True})
            return await self.workspaces.add_member(
                workspace_id=invite.workspace_id,
                user_sub=user_sub,
                role=invite.role,
            )

    async def list_pending(self, *, workspace_id: UUID) -> tuple[Invite, ...]:
        async with self._lock:
            now = self.clock_ms()
            return tuple(
                inv
                for inv in self._by_id.values()
                if inv.workspace_id == workspace_id
                and not inv.accepted
                and inv.expires_at_ms > now
            )
