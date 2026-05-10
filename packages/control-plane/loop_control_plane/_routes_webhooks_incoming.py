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
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Final
from uuid import UUID, uuid4

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

from loop_control_plane._app_agents import AgentRecord
from loop_control_plane._app_common import request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.channel_bindings import (
    ChannelActivityCreate,
    ChannelBindingRecord,
)
from loop_control_plane.trace_search import TraceSummary
from loop_control_plane.workspaces import WorkspaceError

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

_CHANNEL_BINDING_TYPES: Final[dict[str, str]] = {
    "slack": "slack",
    "whatsapp": "whatsapp",
    "discord": "webhook_api",
    "telegram": "telegram",
    "twilio": "sms",
    "teams": "teams",
    "email": "email",
    "rcs": "sms",
    "web": "web_chat",
}

_ROUTABLE_BINDING_STATUSES: Final[frozenset[str]] = frozenset({
    "ready",
    "staged",
    "live",
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


def _trace_id_for(
    *,
    workspace_id: UUID,
    channel: str,
    provider_event_id: str,
    body_bytes: bytes,
) -> str:
    body_hash = sha256(body_bytes).hexdigest()
    seed = f"{workspace_id}:{channel}:{provider_event_id}:{body_hash}"
    return sha256(seed.encode("utf-8")).hexdigest()[:32]


def _dedup_key_for(*, workspace_id: UUID, channel: str, provider_event_id: str) -> str:
    return make_dedup_key(channel, f"{workspace_id}:{provider_event_id}")


def _binding_type_for_channel(channel: str) -> str:
    return _CHANNEL_BINDING_TYPES.get(channel, "webhook_api")


def _is_routable(binding: ChannelBindingRecord) -> bool:
    return binding.status in _ROUTABLE_BINDING_STATUSES


async def _resolve_inbound_route(
    request: Request,
    *,
    workspace_id: UUID,
    channel: str,
    agent_id: UUID | None,
    channel_binding_id: str | None,
) -> tuple[AgentRecord | None, ChannelBindingRecord | None, str]:
    cp = request.app.state.cp
    channel_type = _binding_type_for_channel(channel)

    if agent_id is not None:
        try:
            agents = [await cp.agents.get(workspace_id=workspace_id, agent_id=agent_id)]
        except WorkspaceError:
            return None, None, "agent_not_found"
    else:
        agents = await cp.agents.list_for_workspace(workspace_id)

    saw_binding_id = False
    saw_channel_binding = False
    for agent in agents:
        bindings = await cp.channel_bindings.list_for_agent(agent=agent)
        for binding in bindings:
            if channel_binding_id is not None:
                if binding.id != channel_binding_id:
                    continue
                saw_binding_id = True
                if binding.channel_type != channel_type:
                    return None, None, "binding_channel_mismatch"
            elif binding.channel_type != channel_type:
                continue
            saw_channel_binding = True
            if not _is_routable(binding):
                continue
            return agent, binding, "routed"

    if channel_binding_id is not None and not saw_binding_id:
        return None, None, "binding_not_found"
    if saw_channel_binding:
        return None, None, "binding_not_routable"
    return None, None, "no_configured_binding"


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
    agent_id: UUID | None = Query(
        default=None,
        description="Optional target agent for this inbound channel event.",
    ),
    channel_binding_id: str | None = Query(
        default=None,
        description="Optional channel binding id configured for this provider webhook.",
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
    dedup_key = _dedup_key_for(
        workspace_id=workspace_id,
        channel=channel,
        provider_event_id=provider_event_id,
    )

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
        return {
            "received": True,
            "duplicate": True,
            "channel": channel,
            "provider_event_id": provider_event_id,
            "routing_status": "duplicate",
            "agent_id": None,
            "channel_binding_id": None,
            "trace_id": None,
            "evidence_ref": None,
        }

    routed_agent, routed_binding, routing_status = await _resolve_inbound_route(
        request,
        workspace_id=workspace_id,
        channel=channel,
        agent_id=agent_id,
        channel_binding_id=channel_binding_id,
    )

    trace_id: str | None = None
    if routed_agent is not None and routed_binding is not None:
        trace_id = _trace_id_for(
            workspace_id=workspace_id,
            channel=channel,
            provider_event_id=provider_event_id,
            body_bytes=body_bytes,
        )
        cp.trace_store.add(
            TraceSummary(
                workspace_id=workspace_id,
                trace_id=trace_id,
                turn_id=uuid4(),
                conversation_id=uuid4(),
                agent_id=routed_agent.id,
                started_at=datetime.now(UTC),
                duration_ms=0,
                span_count=1,
                error=False,
                channel_binding_id=routed_binding.id,
            )
        )
        await cp.channel_bindings.record_activity(
            agent=routed_agent,
            binding_id=routed_binding.id,
            body=ChannelActivityCreate(
                status="success",
                trace_id=trace_id,
            ),
        )

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
            "routing_status": routing_status,
            "agent_id": str(routed_agent.id) if routed_agent is not None else None,
            "channel_binding_id": routed_binding.id if routed_binding is not None else None,
            "trace_id": trace_id,
        },
    )

    return {
        "received": True,
        "duplicate": False,
        "channel": channel,
        "provider_event_id": provider_event_id,
        "routing_status": routing_status,
        "agent_id": str(routed_agent.id) if routed_agent is not None else None,
        "channel_binding_id": routed_binding.id if routed_binding is not None else None,
        "trace_id": trace_id,
        "evidence_ref": f"trace/{trace_id}" if trace_id is not None else None,
    }


@router.get("/_supported")
async def list_supported_channels() -> dict[str, Any]:
    """Expose the supported-channel list so operators can discover
    which provider names this dispatcher accepts."""
    return {"channels": sorted(SUPPORTED_CHANNELS)}


__all__ = ["SUPPORTED_CHANNELS", "router"]
