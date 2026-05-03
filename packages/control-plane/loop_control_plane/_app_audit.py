"""Audit JSON helpers for the cp-api app."""

from __future__ import annotations

from typing import Any

from loop_control_plane.audit_events import AuditEvent


def audit_payload(event: AuditEvent) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "occurred_at": event.occurred_at.isoformat(),
        "workspace_id": str(event.workspace_id),
        "actor_sub": event.actor_sub,
        "action": event.action,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "request_id": event.request_id,
        "payload_hash": event.payload_hash,
        "outcome": event.outcome,
    }
