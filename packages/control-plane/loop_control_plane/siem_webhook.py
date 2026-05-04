"""SIEM webhook dispatcher for audit events — S633.

Each workspace may register one HMAC-signed webhook endpoint.  When the
audit logger appends a new :class:`~loop_control_plane.audit_log.AuditEvent`
the dispatcher POSTs a JSON payload to the registered URL.

Design
------
* **Per-workspace configuration** — :class:`SiemWebhookConfig` stores the
  target URL and a shared-secret used for HMAC-SHA-256 signing.
* **Signature** — the ``X-Loop-Signature-256`` header is ``hmac-sha256=<hex>``
  over the raw request body, mirroring the GitHub webhook convention.
  Receivers can verify authenticity before parsing.
* **Back-fill** — :meth:`SiemWebhookDispatcher.backfill` replays all events
  in ``store`` for the workspace to the configured webhook, useful after an
  outage when the receiver missed live deliveries.
* **Transport abstraction** — an injectable ``send_fn`` (default: ``httpx.post``)
  keeps the class testable without network calls.
* **Error handling** — a failed delivery raises :class:`WebhookDeliveryError`
  which callers may catch and queue for retry via their own retry loop.

Supported SIEM targets
-----------------------
``SiemWebhookConfig.target`` is informational only; the dispatcher treats
all targets identically (POST JSON + HMAC header).  The distinction matters
for receiver documentation but not for the dispatcher logic.

    "datadog"  — Datadog Log Management HTTP endpoint
    "splunk"   — Splunk HEC (HTTP Event Collector)
    "generic"  — Any HTTPS receiver (e.g. custom SIEM, Elastic, Sumo Logic)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from loop_control_plane.audit_log import AuditEvent, AuditStore

__all__ = [
    "SiemTarget",
    "SiemWebhookConfig",
    "SiemWebhookDispatcher",
    "WebhookDeliveryError",
]

SiemTarget = Literal["datadog", "splunk", "generic"]

# ---------------------------------------------------------------------------
# In-memory registry (tests / dev)
# ---------------------------------------------------------------------------

_REGISTRY: dict[uuid.UUID, SiemWebhookConfig] = {}


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class SiemWebhookConfig:
    """Per-workspace SIEM webhook registration.

    Attributes
    ----------
    workspace_id:
        The workspace this configuration belongs to.
    url:
        HTTPS endpoint to POST audit events to.
    secret:
        Shared secret for HMAC-SHA-256 signing.  Must be kept confidential.
    target:
        Informational label for the SIEM integration type.
    enabled:
        When ``False`` the dispatcher will skip delivery for this workspace.
    """

    workspace_id: uuid.UUID
    url: str
    secret: str
    target: SiemTarget = "generic"
    enabled: bool = True


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class WebhookDeliveryError(RuntimeError):
    """Raised when the HTTP delivery attempt fails or the receiver returns
    a non-2xx status.

    Attributes
    ----------
    event_id:
        The :class:`~loop_control_plane.audit_log.AuditEvent` that failed.
    status_code:
        HTTP status returned by the receiver, or ``None`` if a network
        error occurred before a response was received.
    """

    def __init__(
        self,
        message: str,
        event_id: uuid.UUID | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.event_id = event_id
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Send function type
# ---------------------------------------------------------------------------

SendFn = Callable[[str, bytes, dict[str, str]], int]
"""Callable that POSTs *body* to *url* with *headers* and returns the HTTP
status code.  The default implementation uses ``httpx``; tests inject a stub.
"""


def _default_send(url: str, body: bytes, headers: dict[str, str]) -> int:
    """Default HTTP sender using ``httpx`` (optional dependency).

    ``httpx`` is available in the control-plane's production environment.
    Unit tests should always inject a stub via ``send_fn`` parameter.
    """
    try:
        import httpx  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "httpx is required for SIEM webhook delivery. "
            "Install it with: pip install httpx"
        ) from exc

    response = httpx.post(url, content=body, headers=headers, timeout=10)
    return response.status_code


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def _event_to_dict(event: AuditEvent) -> dict[str, Any]:
    """Convert an :class:`AuditEvent` to a JSON-serialisable dict."""
    return {
        "id": str(event.id),
        "workspace_id": str(event.workspace_id),
        "action": event.action,
        "resource_type": event.resource_type,
        "resource_id": str(event.resource_id) if event.resource_id else None,
        "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
        "before_state": event.before_state,
        "after_state": event.after_state,
        "client_ip": event.client_ip,
        "user_agent": event.user_agent,
        "request_id": event.request_id,
        "entry_hash": event.entry_hash,
        "previous_hash": event.previous_hash,
        "created_at": event.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Signing
# ---------------------------------------------------------------------------


def _sign(body: bytes, secret: str) -> str:
    """Return the ``X-Loop-Signature-256`` header value for *body*.

    Format: ``hmac-sha256=<lowercase-hex>``
    """
    mac = hmac.new(secret.encode(), body, hashlib.sha256)
    return f"hmac-sha256={mac.hexdigest()}"


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


@dataclass
class SiemWebhookDispatcher:
    """Delivers :class:`AuditEvent` objects to registered SIEM webhooks.

    Parameters
    ----------
    store:
        :class:`~loop_control_plane.audit_log.AuditStore` used for backfill.
    registry:
        Mutable mapping of ``workspace_id → SiemWebhookConfig``.  Defaults
        to the module-level ``_REGISTRY`` singleton.
    send_fn:
        HTTP POST callable.  Override in tests to avoid real network calls.
    """

    store: AuditStore
    registry: dict[uuid.UUID, SiemWebhookConfig] = field(
        default_factory=lambda: _REGISTRY
    )
    send_fn: SendFn = field(default=_default_send, repr=False)

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    def register(self, config: SiemWebhookConfig) -> None:
        """Register or replace a webhook configuration for a workspace."""
        self.registry[config.workspace_id] = config

    def unregister(self, workspace_id: uuid.UUID) -> None:
        """Remove the webhook registration for *workspace_id*, if any."""
        self.registry.pop(workspace_id, None)

    def get_config(self, workspace_id: uuid.UUID) -> SiemWebhookConfig | None:
        """Return the registered config for *workspace_id*, or ``None``."""
        return self.registry.get(workspace_id)

    # ------------------------------------------------------------------
    # Delivery
    # ------------------------------------------------------------------

    def deliver(self, event: AuditEvent) -> None:
        """POST *event* to the workspace's registered SIEM webhook.

        A no-op when no webhook is registered or the config is disabled.

        Raises
        ------
        WebhookDeliveryError
            When the HTTP call fails or the receiver returns a non-2xx code.
        """
        config = self.registry.get(event.workspace_id)
        if config is None or not config.enabled:
            return

        payload = json.dumps(_event_to_dict(event), separators=(",", ":")).encode()
        signature = _sign(payload, config.secret)
        headers = {
            "content-type": "application/json",
            "x-loop-signature-256": signature,
            "x-loop-workspace-id": str(event.workspace_id),
        }

        status = self.send_fn(config.url, payload, headers)
        if not (200 <= status < 300):
            raise WebhookDeliveryError(
                f"SIEM webhook returned HTTP {status} for event {event.id}",
                event_id=event.id,
                status_code=status,
            )

    # ------------------------------------------------------------------
    # Back-fill
    # ------------------------------------------------------------------

    def backfill(self, workspace_id: uuid.UUID) -> int:
        """Replay all stored events for *workspace_id* to the webhook.

        Intended for use after a receiver outage.  Events are delivered in
        insertion order.  Delivery stops on the first failure.

        Returns
        -------
        int
            Number of events successfully delivered.

        Raises
        ------
        WebhookDeliveryError
            On the first event whose delivery fails.
        """
        events = self.store.list_for_workspace(workspace_id)
        delivered = 0
        for event in events:
            self.deliver(event)
            delivered += 1
        return delivered
