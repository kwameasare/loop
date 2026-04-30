"""LiveKit room manager (S368).

Loop creates an ephemeral LiveKit room per voice session: agent joins
as a participant, the user joins via SDK / phone bridge, and the room
is torn down when the call ends. We never call LiveKit's REST API
directly from runtime code — we go through a ``LiveKitClient``
Protocol so the room manager is testable without network and so we
can swap LiveKit Cloud for self-hosted in CLOUD_PORTABILITY.md.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

UTC = UTC

DEFAULT_ROOM_TTL_SECONDS = 60 * 30  # 30 minutes max room lifetime
DEFAULT_PARTICIPANT_TTL_SECONDS = 60 * 60 * 4  # 4 h grace for tokens


class LiveKitError(RuntimeError):
    """LiveKit operation failed."""


class RoomNotFound(LiveKitError):  # noqa: N818
    pass


@dataclass(frozen=True, slots=True)
class RoomGrant:
    """JWT claim subset required for a participant token."""

    room: str
    identity: str
    can_publish: bool
    can_subscribe: bool
    valid_until_ms: int


@dataclass(frozen=True, slots=True)
class Room:
    name: str
    sid: str  # LiveKit-issued SID
    workspace_id: UUID
    agent_id: UUID
    created_at_ms: int
    ttl_seconds: int


@runtime_checkable
class LiveKitClient(Protocol):
    """Subset of livekit-server-sdk we depend on."""

    async def create_room(
        self, *, name: str, empty_timeout_seconds: int, max_participants: int
    ) -> str: ...  # returns sid

    async def delete_room(self, *, name: str) -> None: ...

    def mint_token(self, grant: RoomGrant, *, api_key: str, api_secret: str) -> str: ...


def now_ms_default() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


@dataclass(slots=True)
class RoomManager:
    """Stateful manager: create + bookkeep + teardown rooms."""

    client: LiveKitClient
    api_key: str
    api_secret: str
    now_ms: Callable[[], int] = field(default=now_ms_default)
    rooms: dict[str, Room] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.api_key or not self.api_secret:
            raise ValueError("api_key and api_secret required")

    async def create_room(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        ttl_seconds: int = DEFAULT_ROOM_TTL_SECONDS,
        max_participants: int = 6,
    ) -> Room:
        if ttl_seconds < 30 or ttl_seconds > 60 * 60 * 4:
            raise ValueError("ttl_seconds out of bounds")
        if max_participants < 2:
            raise ValueError("max_participants must be >=2")
        name = _build_room_name(workspace_id, agent_id)
        try:
            sid = await self.client.create_room(
                name=name,
                empty_timeout_seconds=ttl_seconds,
                max_participants=max_participants,
            )
        except Exception as exc:
            raise LiveKitError(f"create_room failed: {exc}") from exc
        room = Room(
            name=name,
            sid=sid,
            workspace_id=workspace_id,
            agent_id=agent_id,
            created_at_ms=self.now_ms(),
            ttl_seconds=ttl_seconds,
        )
        self.rooms[name] = room
        return room

    def mint_participant_token(
        self,
        *,
        room: str,
        identity: str,
        can_publish: bool = True,
        can_subscribe: bool = True,
        ttl_seconds: int = DEFAULT_PARTICIPANT_TTL_SECONDS,
    ) -> str:
        if room not in self.rooms:
            raise RoomNotFound(f"unknown room {room!r}")
        grant = RoomGrant(
            room=room,
            identity=identity,
            can_publish=can_publish,
            can_subscribe=can_subscribe,
            valid_until_ms=self.now_ms() + ttl_seconds * 1000,
        )
        return self.client.mint_token(
            grant, api_key=self.api_key, api_secret=self.api_secret
        )

    async def teardown(self, room_name: str) -> None:
        if room_name not in self.rooms:
            raise RoomNotFound(f"unknown room {room_name!r}")
        try:
            await self.client.delete_room(name=room_name)
        except Exception as exc:
            raise LiveKitError(f"delete_room failed: {exc}") from exc
        self.rooms.pop(room_name, None)

    def is_expired(self, room_name: str) -> bool:
        room = self.rooms.get(room_name)
        if room is None:
            raise RoomNotFound(f"unknown room {room_name!r}")
        return self.now_ms() - room.created_at_ms > room.ttl_seconds * 1000


def _build_room_name(workspace_id: UUID, agent_id: UUID) -> str:
    """LiveKit room names must be url-safe; use a workspace+agent prefix
    plus a random suffix so two concurrent calls don't collide."""
    suffix = secrets.token_urlsafe(8)
    return f"loop-{workspace_id.hex[:8]}-{agent_id.hex[:8]}-{suffix}"


__all__ = [
    "DEFAULT_PARTICIPANT_TTL_SECONDS",
    "DEFAULT_ROOM_TTL_SECONDS",
    "LiveKitClient",
    "LiveKitError",
    "Room",
    "RoomGrant",
    "RoomManager",
    "RoomNotFound",
]
