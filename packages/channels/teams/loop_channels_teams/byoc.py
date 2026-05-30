"""BYOC credential resolution for the Microsoft Teams bot adapter.

Required fields (provider ``teams``):

* ``app_id`` — Azure app registration client id (the bot's identity)
* ``app_password`` — Azure app secret
* ``tenant_id`` — Azure AD tenant id (single-tenant bots) or
  ``"common"`` (multi-tenant)
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from loop_channels_core import (
    ByocCredentialsResolver,
    validate_required_credentials,
)
from loop_channels_core.frames import OutboundFrame

__all__ = [
    "ByocTeamsSender",
    "TeamsMessageSender",
    "TeamsTransportBuilder",
    "build_byoc_teams_sender",
]


_REQUIRED_TEAMS_FIELDS = ("app_id", "app_password", "tenant_id")


class TeamsMessageSender(Protocol):
    """Wraps the actual Bot Framework REST send (POST to the bot's
    ``serviceUrl`` reply endpoint)."""

    def send(
        self,
        *,
        frame: OutboundFrame,
        conversation_ref: dict[str, Any],
        reply_to_id: str | None = None,
    ) -> dict[str, Any]: ...


class TeamsTransportBuilder(Protocol):
    def __call__(self, credentials: dict[str, Any]) -> TeamsMessageSender: ...


def _validate(creds: dict[str, Any]) -> None:
    validate_required_credentials(
        creds, required=_REQUIRED_TEAMS_FIELDS, provider="teams"
    )


def build_byoc_teams_sender(
    *,
    agent_id: UUID,
    resolver: ByocCredentialsResolver,
    transport_builder: TeamsTransportBuilder,
    channel_type: str = "teams",
) -> TeamsMessageSender:
    creds = resolver(agent_id=agent_id, channel_type=channel_type)
    _validate(creds)
    return transport_builder(creds)


class ByocTeamsSender:
    def __init__(
        self,
        *,
        agent_id: UUID,
        resolver: ByocCredentialsResolver,
        transport_builder: TeamsTransportBuilder,
        channel_type: str = "teams",
    ) -> None:
        self._agent_id = agent_id
        self._channel_type = channel_type
        self._resolver = resolver
        self._transport_builder = transport_builder

    def send(
        self,
        *,
        frame: OutboundFrame,
        conversation_ref: dict[str, Any],
        reply_to_id: str | None = None,
    ) -> dict[str, Any]:
        creds = self._resolver(
            agent_id=self._agent_id, channel_type=self._channel_type
        )
        _validate(creds)
        upstream = self._transport_builder(creds)
        return upstream.send(
            frame=frame,
            conversation_ref=conversation_ref,
            reply_to_id=reply_to_id,
        )
