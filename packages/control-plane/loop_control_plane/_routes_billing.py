"""Workspace-scoped billing routes for Studio."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access

router = APIRouter(prefix="/v1/workspaces", tags=["Billing"])

_APP_BASE_URL = "https://app.loop.dev"

_PLAN: dict[str, Any] = {
    "id": "growth",
    "name": "Growth",
    "monthly_price_cents": 19_900,
    "included_messages": 150_000,
    "overage_per_message_cents": 1,
    "features": [
        "Unlimited agents",
        "Priority support",
        "90-day trace retention",
        "Custom domains",
    ],
}


class PaymentMethodBody(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    cardholder_name: str = Field(
        alias="cardholderName",
        min_length=1,
        max_length=120,
    )
    setup_intent_id: str | None = Field(default=None, min_length=1, max_length=200)


def _month_window(now: datetime | None = None) -> tuple[int, int]:
    current = now or datetime.now(UTC)
    start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return (
        int(start.timestamp() * 1000),
        int(end.timestamp() * 1000),
    )


def _last4_from_setup_intent(setup_intent_id: str | None) -> str:
    if not setup_intent_id:
        return "4242"
    digits = "".join(ch for ch in setup_intent_id if ch.isdigit())
    return (digits[-4:] if len(digits) >= 4 else digits.rjust(4, "0")) or "4242"


def _message_usage(events: list[Any], workspace_id: UUID, start_ms: int, end_ms: int) -> int:
    aliases = {"messages", "turns", "agent_turns"}
    return sum(
        event.quantity
        for event in events
        if event.workspace_id == workspace_id
        and start_ms <= event.timestamp_ms < end_ms
        and event.metric in aliases
    )


def _summary(cp: Any, workspace_id: UUID) -> dict[str, Any]:
    start_ms, end_ms = _month_window()
    events = cp.usage_ledger.window(start_ms=start_ms, end_ms=end_ms)
    mtd_messages = _message_usage(events, workspace_id, start_ms, end_ms)
    overage = max(0, mtd_messages - int(_PLAN["included_messages"]))
    mtd_cost_cents = int(_PLAN["monthly_price_cents"]) + (
        overage * int(_PLAN["overage_per_message_cents"])
    )
    payment = cp.billing_payment_methods.get(workspace_id)
    return {
        "workspace_id": str(workspace_id),
        "plan": dict(_PLAN),
        "cycle_start_ms": start_ms,
        "cycle_end_ms": end_ms,
        "mtd_messages": mtd_messages,
        "mtd_cost_cents": mtd_cost_cents,
        "payment_method_last4": payment["last4"] if payment else None,
        "customer_portal_url": f"{_APP_BASE_URL}/workspaces/{workspace_id}/billing/portal",
    }


def _invoice_from_summary(summary: dict[str, Any]) -> dict[str, Any]:
    date_ms = int(summary["cycle_start_ms"])
    dt = datetime.fromtimestamp(date_ms / 1000, UTC)
    invoice_id = f"loop_{summary['workspace_id']}_{dt:%Y%m}"
    return {
        "id": invoice_id,
        "number": f"LOOP-{dt:%Y-%m}",
        "date_ms": date_ms,
        "amount_cents": int(summary["mtd_cost_cents"]),
        "status": "open",
        "pdf_url": f"{_APP_BASE_URL}/billing/invoices/{invoice_id}.pdf",
    }


@router.get("/{workspace_id}/billing")
async def get_billing_summary(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    return _summary(cp, workspace_id)


@router.get("/{workspace_id}/billing/invoices")
async def get_billing_invoices(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    items = cp.billing_invoices.get(workspace_id)
    if items is None:
        items = [_invoice_from_summary(_summary(cp, workspace_id))]
    return {"items": items}


@router.post("/{workspace_id}/billing/payment-method")
async def update_billing_payment_method(
    request: Request,
    workspace_id: UUID,
    body: PaymentMethodBody,
    caller_sub: str = CALLER,
) -> dict[str, str]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    last4 = _last4_from_setup_intent(body.setup_intent_id)
    cp.billing_payment_methods[workspace_id] = {
        "last4": last4,
        "cardholder_name": body.cardholder_name.strip(),
        "setup_intent_id": body.setup_intent_id,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="billing:payment_method:update",
        resource_type="billing_payment_method",
        store=cp.audit_events,
        resource_id=str(workspace_id),
        request_id=request_id(request),
        payload={
            "last4": last4,
            "cardholder_name": body.cardholder_name.strip(),
            "has_setup_intent": body.setup_intent_id is not None,
        },
    )
    return {"last4": last4}


__all__ = ["router"]
