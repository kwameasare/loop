"""Shared BYOC (Bring-Your-Own-Credentials) types for channel adapters.

Every channel adapter (Twilio SMS, Meta WhatsApp, Slack, Teams,
Telegram, Discord, SMTP email, …) resolves provider credentials at
send time through the same :class:`ByocCredentialsResolver`
Protocol. Production wires the resolver to cp's encrypted store; the
adapter never holds long-lived plaintext credentials.

This module is intentionally tiny — types that every channel package
imports — to avoid a circular dep between `loop_channels_core` and
the per-channel packages.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol
from uuid import UUID

__all__ = [
    "ByocCredentialsError",
    "ByocCredentialsResolver",
    "validate_required_credentials",
]


class ByocCredentialsError(ValueError):
    """Resolved credentials are missing one or more required fields.

    Adapters raise this when the resolver's payload doesn't carry
    everything the provider needs. The caller (cp route or operator
    surface) translates to a 4xx with the field list.
    """


class ByocCredentialsResolver(Protocol):
    """Sync callable that returns a credentials payload for an
    ``(agent_id, channel_type)`` pair.

    Production wraps cp's async ``byoc_secrets.reveal_for_adapter``
    in a sync bridge (see ``loop_control_plane._byoc_bridge``).
    Tests pass a stub dict-returning closure.
    """

    def __call__(
        self, *, agent_id: UUID, channel_type: str
    ) -> dict[str, Any]: ...


def validate_required_credentials(
    credentials: dict[str, Any],
    *,
    required: Iterable[str],
    provider: str,
) -> None:
    """Raise :class:`ByocCredentialsError` if any ``required`` key is
    missing or falsy from ``credentials``.

    Channel adapters call this on the resolved payload before they
    construct an upstream transport. Centralising it here keeps the
    failure message uniform across providers and gives every channel
    BYOC seam the same shape.
    """
    missing = [key for key in required if not credentials.get(key)]
    if missing:
        raise ByocCredentialsError(
            f"BYOC {provider} credentials missing required fields: {missing}"
        )
