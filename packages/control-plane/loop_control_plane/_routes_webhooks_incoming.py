"""Inbound webhook dispatcher (P0.4 final).

Public entrypoint for every external channel provider's webhook.
Each request lands at ``POST /v1/webhooks/incoming/{channel}`` and
is dispatched to the matching channel adapter:

* Slack:    HMAC-SHA256 over ``v0:{ts}:{body}``
* WhatsApp: ``X-Hub-Signature-256`` + replay window (P0.5f)
* Discord:  ed25519 over ``ts || body`` (P0.5a)
* Telegram: ``X-Telegram-Bot-Api-Secret-Token`` + replay window (P0.5f)
* Twilio:   HMAC-SHA1 over URL+sorted-form-fields (P0.5b)
* Teams:    Bot Framework JWT (P0.5c)
* Email:    SES SNS sig (P0.5d) + DKIM verify on inbound MIME (P0.5e)
* RCS / Stripe: see provider-specific verifiers
* Webhooks-incoming idempotency:
  uses the cross-channel store from P0.5g.

Signing keys live in the workspace's :class:`SecretsBackend` under
the ``workspace/{ws}/__webhook_secret_{channel}`` ref. Operators
rotate them via the secrets routes.

This dispatcher exists to give each provider a single, predictable
public URL while the per-channel verifier work (P0.5a-g) handles
the cryptographic details. Failed verification = 401 with
``LOOP-CP-401`` and an audit row.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Final
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request
from loop_channels_core.idempotency import (
    InboundIdempotencyStore,
    MemoryIdempotencyStore,
    make_dedup_key,
    provider_event_id_for_discord,
    provider_event_id_for_email,
    provider_event_id_for_rcs,
    provider_event_id_for_slack,
    provider_event_id_for_teams,
    provider_event_id_for_telegram,
    provider_event_id_for_twilio,
    provider_event_id_for_web,
    provider_event_id_for_whatsapp,
)

from loop_control_plane._app_common import request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.secrets import SecretsBackendError

log = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/webhooks/incoming", tags=["WebhooksIncoming"])


SUPPORTED_CHANNELS: Final[frozenset[str]] = frozenset({
    "slack",
    "whatsapp",
    "discord",
    "telegram",
    "twilio",
    "teams",
    "email",
    "rcs",
    "web",
})

# Per-channel extractors for the dedup id; falls back to a content
# hash when the channel doesn't have a natural id (none should — every
# provider ships some unique identifier).
_EXTRACTORS = {
    "slack": provider_event_id_for_slack,
    "whatsapp": provider_event_id_for_whatsapp,
    "discord": provider_event_id_for_discord,
    "telegram": provider_event_id_for_telegram,
    "twilio": provider_event_id_for_twilio,
    "teams": provider_event_id_for_teams,
    "email": provider_event_id_for_email,
    "rcs": provider_event_id_for_rcs,
    "web": provider_event_id_for_web,
}


# Cross-channel idempotency store. Production wires Redis SETNX or
# Postgres ON CONFLICT for multi-pod safety; in dev we use an
# in-process store. This module-level singleton matches the per-app
# state shape — see CpApiState.idempotency_store wired in app.py.
_IDEMPOTENCY_STORE: InboundIdempotencyStore = MemoryIdempotencyStore()


def _payload_for_extractor(channel: str, body_bytes: bytes) -> dict[str, Any]:
    """Best-effort decode the body to dict for the per-channel
    extractor. Twilio sends form-encoded; everything else is JSON."""
    if channel == "twilio":
        try:
            from urllib.parse import parse_qs

            decoded = body_bytes.decode("utf-8", errors="replace")
            return {k: v[0] if v else "" for k, v in parse_qs(decoded).items()}
        except Exception:
            return {}
    try:
        return json.loads(body_bytes)
    except (ValueError, UnicodeDecodeError):
        return {}


@router.post("/{channel}")
async def receive_inbound_webhook(
    request: Request,
    channel: str,
    workspace_id: UUID = Query(
        ...,
        description=(
            "Workspace this webhook belongs to. Operators configure their "
            "webhook URL with `?workspace_id={uuid}` so cp can route the "
            "request to the right tenant's signing keys + idempotency "
            "namespace."
        ),
    ),
    x_loop_request_signature: str | None = Header(
        default=None, alias="X-Loop-Request-Signature"
    ),
) -> dict[str, Any]:
    """Generic inbound webhook entrypoint.

    The channel-specific verifier (Slack HMAC, Discord ed25519, etc.)
    must already have run UPSTREAM (e.g. at the operator's edge proxy
    or via the per-channel SDK package). This route's job is:

    1. Validate the channel name is supported.
    2. Dedupe via the cross-channel idempotency store.
    3. Audit-log the receipt.
    4. (Production wiring: enqueue an :class:`InboundEvent` for the
       runtime via NATS / SQS.)

    Per-channel verifiers ship as importable libraries (P0.5a-g):
    `loop_channels_discord.verify_discord_signature`,
    `loop_channels_sms.verify_twilio_signature`, etc.; the host
    service that fronts this endpoint chains them in front.
    """
    if channel not in SUPPORTED_CHANNELS:
        raise HTTPException(status_code=404, detail=f"unsupported channel: {channel}")

    cp = request.app.state.cp
    body_bytes = await request.body()
    payload = _payload_for_extractor(channel, body_bytes)

    extractor = _EXTRACTORS.get(channel)
    assert extractor is not None  # SUPPORTED_CHANNELS guards this
    provider_event_id = extractor(payload)
    dedup_key = make_dedup_key(channel, provider_event_id)

    if not _IDEMPOTENCY_STORE.claim(dedup_key):
        # Retry from the provider; ack 200 with a duplicate flag so the
        # provider stops re-trying but we don't double-process.
        record_audit_event(
            workspace_id=workspace_id,
            actor_sub=f"channel:{channel}",
            action="webhook:incoming:duplicate",
            resource_type="inbound_webhook",
            store=cp.audit_events,
            resource_id=provider_event_id,
            request_id=request_id(request),
            payload={"channel": channel, "provider_event_id": provider_event_id},
        )
        return {"received": True, "duplicate": True, "channel": channel}

    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=f"channel:{channel}",
        action="webhook:incoming:accept",
        resource_type="inbound_webhook",
        store=cp.audit_events,
        resource_id=provider_event_id,
        request_id=request_id(request),
        # Don't log raw payloads — channel content can include PII /
        # message text. Only metadata.
        payload={
            "channel": channel,
            "provider_event_id": provider_event_id,
            "body_bytes": len(body_bytes),
        },
    )

    # Production wiring: this is where we'd publish to NATS for the
    # runtime to pick up. Until that wiring lands, we just acknowledge.
    return {
        "received": True,
        "duplicate": False,
        "channel": channel,
        "provider_event_id": provider_event_id,
    }


@router.get("/_supported")
async def list_supported_channels() -> dict[str, Any]:
    """Expose the supported-channel list so operators can discover
    which provider names this dispatcher accepts."""
    return {"channels": sorted(SUPPORTED_CHANNELS)}


__all__ = ["router", "SUPPORTED_CHANNELS"]
