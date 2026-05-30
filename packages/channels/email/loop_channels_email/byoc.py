"""BYOC credential resolution for the SMTP email adapter.

The studio's channel-binding form offers an SMTP-relay provider
(``email_smtp``) alongside SES; this module handles the SMTP path so
operators can BYO any SMTP server (Postmark, SendGrid, their own
on-prem relay).

Required fields (provider ``email_smtp``):

* ``host`` — SMTP server hostname
* ``port`` — SMTP port (typically ``587`` for STARTTLS,
  ``465`` for implicit TLS)
* ``username`` — SMTP auth login (often the from-address)
* ``password`` — SMTP auth password
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
    "ByocSmtpSender",
    "SmtpMessageSender",
    "SmtpTransportBuilder",
    "build_byoc_smtp_sender",
]


_REQUIRED_SMTP_FIELDS = ("host", "port", "username", "password")


class SmtpMessageSender(Protocol):
    """Wraps the actual SMTP submission (``smtplib.SMTP`` /
    ``aiosmtplib`` / etc.). The injected concrete impl receives the
    Loop frame, the recipient and sender addresses, and returns the
    server's accept/queue acknowledgment."""

    def send(
        self,
        *,
        frame: OutboundFrame,
        to: str,
        sender: str,
        subject: str,
        in_reply_to: str | None = None,
    ) -> dict[str, Any]: ...


class SmtpTransportBuilder(Protocol):
    def __call__(self, credentials: dict[str, Any]) -> SmtpMessageSender: ...


def _validate(creds: dict[str, Any]) -> None:
    validate_required_credentials(
        creds, required=_REQUIRED_SMTP_FIELDS, provider="email_smtp"
    )


def build_byoc_smtp_sender(
    *,
    agent_id: UUID,
    resolver: ByocCredentialsResolver,
    transport_builder: SmtpTransportBuilder,
    channel_type: str = "email",
) -> SmtpMessageSender:
    creds = resolver(agent_id=agent_id, channel_type=channel_type)
    _validate(creds)
    return transport_builder(creds)


class ByocSmtpSender:
    def __init__(
        self,
        *,
        agent_id: UUID,
        resolver: ByocCredentialsResolver,
        transport_builder: SmtpTransportBuilder,
        channel_type: str = "email",
    ) -> None:
        self._agent_id = agent_id
        self._channel_type = channel_type
        self._resolver = resolver
        self._transport_builder = transport_builder

    def send(
        self,
        *,
        frame: OutboundFrame,
        to: str,
        sender: str,
        subject: str,
        in_reply_to: str | None = None,
    ) -> dict[str, Any]:
        creds = self._resolver(
            agent_id=self._agent_id, channel_type=self._channel_type
        )
        _validate(creds)
        upstream = self._transport_builder(creds)
        return upstream.send(
            frame=frame,
            to=to,
            sender=sender,
            subject=subject,
            in_reply_to=in_reply_to,
        )
