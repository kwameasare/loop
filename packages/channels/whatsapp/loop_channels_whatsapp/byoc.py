"""BYOC credential resolution for the Meta WhatsApp Business adapter.

The enterprise admin pastes their WhatsApp Business phone number id,
access token, and (optionally) waba id into the studio's
channel-binding form. cp encrypts and stores them. At send time the
WhatsApp dispatcher resolves the plaintext through this module —
nothing here keeps a long-lived token in process memory.

Required fields (provider ``meta_whatsapp``):

* ``phone_number_id`` — Meta numeric phone-number id (Cloud API)
* ``access_token`` — permanent system-user token
* ``webhook_verify_token`` — operator-chosen string used in webhook
  GET ``hub.challenge`` handshake (consumed by the inbound side)

Optional:

* ``business_account_id`` — WABA id, used by template-management
  helpers; not strictly required for plain send.
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
    "ByocWhatsAppSender",
    "WhatsAppMessageSender",
    "WhatsAppTransportBuilder",
    "build_byoc_whatsapp_sender",
]


_REQUIRED_WHATSAPP_FIELDS = (
    "phone_number_id",
    "access_token",
    "webhook_verify_token",
)


class WhatsAppMessageSender(Protocol):
    """Wraps the actual Cloud API POST (``/v18.0/{phone}/messages``).

    The injected concrete implementation knows how to translate a
    Loop :class:`OutboundFrame` into the Cloud API JSON envelope and
    submit it with the resolved bearer token. Returning the raw
    Cloud API response keeps audit/idempotency callers free to
    extract ``messages[0].id`` themselves.
    """

    def send(self, *, frame: OutboundFrame, to: str) -> dict[str, Any]: ...


class WhatsAppTransportBuilder(Protocol):
    """Builds a :class:`WhatsAppMessageSender` from a resolved creds
    dict. Injected so this package doesn't take a dep on httpx /
    requests; production wires it to a function that constructs a
    Cloud API client with the resolved bearer token."""

    def __call__(self, credentials: dict[str, Any]) -> WhatsAppMessageSender: ...


def _validate(creds: dict[str, Any]) -> None:
    validate_required_credentials(
        creds, required=_REQUIRED_WHATSAPP_FIELDS, provider="meta_whatsapp"
    )


def build_byoc_whatsapp_sender(
    *,
    agent_id: UUID,
    resolver: ByocCredentialsResolver,
    transport_builder: WhatsAppTransportBuilder,
    channel_type: str = "whatsapp",
) -> WhatsAppMessageSender:
    """Resolve creds once + build a sender for ``agent_id``.

    Returns the per-call sender if you want rotation-on-every-send;
    otherwise this single instance is bound to the credentials live
    at construction time. Callers that need rotation should construct
    :class:`ByocWhatsAppSender` directly."""
    creds = resolver(agent_id=agent_id, channel_type=channel_type)
    _validate(creds)
    return transport_builder(creds)


class ByocWhatsAppSender:
    """Per-call cred-resolving WhatsApp sender. Resolves + rebuilds
    the underlying transport on every ``send`` so an operator's
    rotation in the studio is picked up by the next outbound
    message."""

    def __init__(
        self,
        *,
        agent_id: UUID,
        resolver: ByocCredentialsResolver,
        transport_builder: WhatsAppTransportBuilder,
        channel_type: str = "whatsapp",
    ) -> None:
        self._agent_id = agent_id
        self._channel_type = channel_type
        self._resolver = resolver
        self._transport_builder = transport_builder

    def send(self, *, frame: OutboundFrame, to: str) -> dict[str, Any]:
        creds = self._resolver(
            agent_id=self._agent_id, channel_type=self._channel_type
        )
        _validate(creds)
        upstream = self._transport_builder(creds)
        return upstream.send(frame=frame, to=to)
