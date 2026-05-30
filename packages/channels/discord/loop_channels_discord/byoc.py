"""BYOC credential resolution for the Discord application adapter.

Required fields (provider ``discord``):

* ``bot_token`` — ``MT…`` bot token from the Discord developer portal
* ``application_id`` — application snowflake id (used for interaction
  follow-up calls)

The Discord ``public_key`` (used to verify interaction signatures
on the inbound side) is treated as part of the same credentials
payload by the cp BYOC route; not required for plain outbound send.
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
    "ByocDiscordSender",
    "DiscordMessageSender",
    "DiscordTransportBuilder",
    "build_byoc_discord_sender",
]


_REQUIRED_DISCORD_FIELDS = ("bot_token", "application_id")


class DiscordMessageSender(Protocol):
    """Wraps the actual Discord REST follow-up POST (``POST
    /webhooks/{application_id}/{interaction_token}``)."""

    def send(
        self,
        *,
        frame: OutboundFrame,
        interaction_token: str,
    ) -> dict[str, Any]: ...


class DiscordTransportBuilder(Protocol):
    def __call__(self, credentials: dict[str, Any]) -> DiscordMessageSender: ...


def _validate(creds: dict[str, Any]) -> None:
    validate_required_credentials(
        creds, required=_REQUIRED_DISCORD_FIELDS, provider="discord"
    )


def build_byoc_discord_sender(
    *,
    agent_id: UUID,
    resolver: ByocCredentialsResolver,
    transport_builder: DiscordTransportBuilder,
    channel_type: str = "discord",
) -> DiscordMessageSender:
    creds = resolver(agent_id=agent_id, channel_type=channel_type)
    _validate(creds)
    return transport_builder(creds)


class ByocDiscordSender:
    def __init__(
        self,
        *,
        agent_id: UUID,
        resolver: ByocCredentialsResolver,
        transport_builder: DiscordTransportBuilder,
        channel_type: str = "discord",
    ) -> None:
        self._agent_id = agent_id
        self._channel_type = channel_type
        self._resolver = resolver
        self._transport_builder = transport_builder

    def send(
        self, *, frame: OutboundFrame, interaction_token: str
    ) -> dict[str, Any]:
        creds = self._resolver(
            agent_id=self._agent_id, channel_type=self._channel_type
        )
        _validate(creds)
        upstream = self._transport_builder(creds)
        return upstream.send(frame=frame, interaction_token=interaction_token)
