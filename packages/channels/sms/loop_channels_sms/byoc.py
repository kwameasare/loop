"""BYOC credential resolution for the SMS adapter.

The enterprise admin pastes their Twilio account SID, auth token, and
from-number into the studio's channel-binding form. cp encrypts and
stores them. At send-time the SMS adapter resolves the plaintext via
this module — never holding the token in long-lived process state.

Two seams:

* :class:`ByocCredentialsResolver` — Protocol the adapter calls to
  fetch the latest credentials dict. Production wires this to a sync
  wrapper around ``cp.byoc_secrets.reveal_for_adapter``; tests inject
  a stub dict.
* :func:`build_byoc_twilio_adapter` — constructs a fully-wired
  :class:`TwilioSmsAdapter` from a freshly-resolved credentials
  payload. Operators rotate creds in the studio; the next adapter
  instance picks up the new value.

The credentials dict shape (provider ``twilio``) the resolver must
return:

* ``account_sid``: Twilio AC… string
* ``auth_token``: Twilio auth token
* ``from_number``: E.164 origin number (e.g. ``+15551234567``)
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from loop_channels_core import (
    ByocCredentialsError,
    ByocCredentialsResolver,
    validate_required_credentials,
)

from loop_channels_sms.compliance import ComplianceKeywordHandler
from loop_channels_sms.twilio import (
    SmsOutboundMessage,
    TwilioSendResult,
    TwilioSmsAdapter,
    TwilioSmsClient,
)


class TwilioTransportBuilder(Protocol):
    """Builds a :class:`TwilioSmsClient` from a resolved creds dict.

    The builder is injected so we don't take a hard dep on the Twilio
    SDK from this package. Production wires it to a function that
    constructs ``twilio.rest.Client(account_sid, auth_token)`` and
    adapts ``.messages.create(...)`` into :class:`TwilioSendResult`.
    """

    def __call__(self, credentials: dict[str, Any]) -> TwilioSmsClient: ...


_REQUIRED_TWILIO_FIELDS = ("account_sid", "auth_token", "from_number")


def _validate_twilio_credentials(creds: dict[str, Any]) -> None:
    validate_required_credentials(
        creds, required=_REQUIRED_TWILIO_FIELDS, provider="twilio"
    )


def build_byoc_twilio_adapter(
    *,
    agent_id: UUID,
    resolver: ByocCredentialsResolver,
    transport_builder: TwilioTransportBuilder,
    compliance: ComplianceKeywordHandler,
    channel_type: str = "sms",
) -> TwilioSmsAdapter:
    """Resolve creds + assemble a Twilio SMS adapter for one agent.

    Raises :class:`ByocCredentialsError` if the resolver returns a
    payload missing any of ``account_sid``, ``auth_token``, or
    ``from_number`` — those are the three Twilio needs to send.

    Operators rotate creds via ``PUT /v1/agents/{agent_id}/channels/
    {channel_type}/credentials``; callers that want the new value
    rebuild the adapter (typically once per outbound dispatch or per
    conversation).
    """
    creds = resolver(agent_id=agent_id, channel_type=channel_type)
    _validate_twilio_credentials(creds)
    client = transport_builder(creds)
    return TwilioSmsAdapter(
        client=client,
        from_number=str(creds["from_number"]),
        compliance=compliance,
    )


class ByocTwilioSmsClient:
    """Per-call cred-resolving :class:`TwilioSmsClient`.

    Use this when you want to keep a long-lived :class:`TwilioSmsAdapter`
    (e.g. cached on a session) and still pick up rotated credentials
    without rebuilding it. Each ``send_message`` re-resolves and
    rebuilds the upstream transport.

    Note: this does NOT update ``TwilioSmsAdapter.from_number`` — that
    field lives on the adapter. Use :func:`build_byoc_twilio_adapter`
    if the from-number can rotate too.
    """

    def __init__(
        self,
        *,
        agent_id: UUID,
        resolver: ByocCredentialsResolver,
        transport_builder: TwilioTransportBuilder,
        channel_type: str = "sms",
    ) -> None:
        self._agent_id = agent_id
        self._channel_type = channel_type
        self._resolver = resolver
        self._transport_builder = transport_builder

    def send_message(self, message: SmsOutboundMessage) -> TwilioSendResult:
        creds = self._resolver(
            agent_id=self._agent_id, channel_type=self._channel_type
        )
        _validate_twilio_credentials(creds)
        upstream = self._transport_builder(creds)
        return upstream.send_message(message)


__all__ = [
    "ByocCredentialsError",
    "ByocCredentialsResolver",
    "ByocTwilioSmsClient",
    "TwilioTransportBuilder",
    "build_byoc_twilio_adapter",
]
