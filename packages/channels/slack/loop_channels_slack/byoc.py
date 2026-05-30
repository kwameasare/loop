"""BYOC credential resolution for the Slack adapter.

Required fields (provider ``slack``):

* ``bot_token`` — ``xoxb-…`` token from the operator's Slack OAuth app
* ``signing_secret`` — used to verify Slack's webhook signatures
  (consumed by the inbound side)
* ``app_id`` — ``A…`` Slack app id; emitted on outbound payloads
  for operator audit
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
    "ByocSlackSender",
    "SlackMessageSender",
    "SlackTransportBuilder",
    "build_byoc_slack_sender",
]


_REQUIRED_SLACK_FIELDS = ("bot_token", "signing_secret", "app_id")


class SlackMessageSender(Protocol):
    """Wraps the actual Slack Web API POST (``chat.postMessage``)."""

    def send(self, *, frame: OutboundFrame, channel: str) -> dict[str, Any]: ...


class SlackTransportBuilder(Protocol):
    def __call__(self, credentials: dict[str, Any]) -> SlackMessageSender: ...


def _validate(creds: dict[str, Any]) -> None:
    validate_required_credentials(
        creds, required=_REQUIRED_SLACK_FIELDS, provider="slack"
    )


def build_byoc_slack_sender(
    *,
    agent_id: UUID,
    resolver: ByocCredentialsResolver,
    transport_builder: SlackTransportBuilder,
    channel_type: str = "slack",
) -> SlackMessageSender:
    creds = resolver(agent_id=agent_id, channel_type=channel_type)
    _validate(creds)
    return transport_builder(creds)


class ByocSlackSender:
    """Per-call cred-resolving Slack sender for rotation-on-send."""

    def __init__(
        self,
        *,
        agent_id: UUID,
        resolver: ByocCredentialsResolver,
        transport_builder: SlackTransportBuilder,
        channel_type: str = "slack",
    ) -> None:
        self._agent_id = agent_id
        self._channel_type = channel_type
        self._resolver = resolver
        self._transport_builder = transport_builder

    def send(self, *, frame: OutboundFrame, channel: str) -> dict[str, Any]:
        creds = self._resolver(
            agent_id=self._agent_id, channel_type=self._channel_type
        )
        _validate(creds)
        upstream = self._transport_builder(creds)
        return upstream.send(frame=frame, channel=channel)
