"""HTTP-shaped facade over :class:`InboxQueue`.

Framework-agnostic: every method takes a JSON-shaped ``dict`` and
returns a JSON-shaped ``dict``, mirroring the eventual REST routes:

* ``POST /v1/workspaces/{workspace_id}/inbox/escalate``  -> ``escalate``
* ``GET  /v1/workspaces/{workspace_id}/inbox/pending``   -> ``list_pending``
* ``POST /v1/inbox/{item_id}/claim``                     -> ``claim``
* ``POST /v1/inbox/{item_id}/release``                   -> ``release``
* ``POST /v1/inbox/{item_id}/resolve``                   -> ``resolve``

The service raises :class:`InboxError` on bad transitions; callers map
that to HTTP 409. Validation errors raise :class:`InboxError` too;
callers map those to HTTP 400.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from loop_control_plane.inbox import InboxError, InboxItem, InboxQueue


def _serialise(item: InboxItem) -> dict[str, Any]:
    return item.model_dump(mode="json")


def _require_uuid(name: str, value: object) -> UUID:
    if not isinstance(value, str):
        raise InboxError(f"{name} must be a UUID string")
    try:
        return UUID(value)
    except ValueError as exc:
        raise InboxError(f"{name} is not a valid UUID") from exc


def _require_str(name: str, value: object, *, min_length: int = 1) -> str:
    if not isinstance(value, str) or len(value) < min_length:
        raise InboxError(f"{name} must be a non-empty string")
    return value


def _require_int(name: str, value: object, *, ge: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < ge:
        raise InboxError(f"{name} must be an integer >= {ge}")
    return value


@dataclass
class InboxAPI:
    """Thin façade so HTTP routers stay one-liners."""

    queue: InboxQueue

    def escalate(self, *, workspace_id: UUID, body: dict[str, Any]) -> dict[str, Any]:
        item = self.queue.escalate(
            workspace_id=workspace_id,
            agent_id=_require_uuid("agent_id", body.get("agent_id")),
            conversation_id=_require_uuid(
                "conversation_id", body.get("conversation_id")
            ),
            user_id=_require_str("user_id", body.get("user_id")),
            reason=_require_str("reason", body.get("reason")),
            now_ms=_require_int("now_ms", body.get("now_ms")),
            last_message_excerpt=str(body.get("last_message_excerpt", "")),
        )
        return _serialise(item)

    def list_pending(self, *, workspace_id: UUID) -> dict[str, Any]:
        items = self.queue.list_pending(workspace_id)
        return {"items": [_serialise(i) for i in items]}

    def claim(self, *, item_id: UUID, body: dict[str, Any]) -> dict[str, Any]:
        item = self.queue.claim(
            item_id,
            operator_id=_require_str("operator_id", body.get("operator_id")),
            now_ms=_require_int("now_ms", body.get("now_ms")),
        )
        return _serialise(item)

    def release(self, *, item_id: UUID) -> dict[str, Any]:
        return _serialise(self.queue.release(item_id))

    def resolve(self, *, item_id: UUID, body: dict[str, Any]) -> dict[str, Any]:
        item = self.queue.resolve(
            item_id, now_ms=_require_int("now_ms", body.get("now_ms"))
        )
        return _serialise(item)


__all__ = ["InboxAPI"]
