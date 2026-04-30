"""Stripe webhook receiver: signature verification + event dispatch.

The real ``stripe`` SDK is intentionally not imported here -- our
cloud-portability rules forbid binding a vendor SDK in a generic
package. We re-implement Stripe's signed-webhook verification
(``Stripe-Signature: t=<ts>,v1=<sig>``) using ``hmac.compare_digest``
so the control-plane stays SDK-free and unit-testable without network.

The dispatcher routes parsed events to per-event handlers registered
by the application (S323 customer.subscription.* and S324 invoice.*).
Handlers are sync callables to keep this module dependency-light;
async work is the application's responsibility.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any


class StripeWebhookError(ValueError):
    """Signature mismatch, malformed header, or stale timestamp."""


def _split_sig_header(header: str) -> tuple[int, list[str]]:
    """Parse ``t=<ts>,v1=<sig>[,v1=<sig>...]`` form."""

    parts: dict[str, list[str]] = {}
    for chunk in header.split(","):
        if "=" not in chunk:
            raise StripeWebhookError(f"malformed signature segment: {chunk!r}")
        key, _, value = chunk.partition("=")
        parts.setdefault(key.strip(), []).append(value.strip())
    if "t" not in parts or "v1" not in parts:
        raise StripeWebhookError("missing t or v1 in Stripe-Signature header")
    try:
        ts = int(parts["t"][0])
    except ValueError as exc:
        raise StripeWebhookError("non-integer timestamp in Stripe-Signature") from exc
    return ts, parts["v1"]


def verify_signature(
    *,
    payload: bytes,
    header: str,
    secret: str,
    now_ms: int,
    tolerance_s: int = 300,
) -> None:
    """Raise ``StripeWebhookError`` unless ``payload`` is authentic.

    The payload is the **raw** request body (UTF-8 bytes). The signed
    string is ``f"{ts}.{payload}"``. Tolerance defaults to Stripe's
    documented 5-minute window to mitigate replay.
    """

    if not secret:
        raise StripeWebhookError("empty webhook secret")
    ts, candidates = _split_sig_header(header)
    drift_s = abs(now_ms // 1000 - ts)
    if drift_s > tolerance_s:
        raise StripeWebhookError(f"timestamp outside tolerance ({drift_s}s)")
    signed = f"{ts}.".encode() + payload
    expected = hmac.new(
        secret.encode("utf-8"), signed, hashlib.sha256
    ).hexdigest()
    for v1 in candidates:
        if hmac.compare_digest(v1, expected):
            return
    raise StripeWebhookError("signature mismatch")


@dataclass(frozen=True)
class StripeEvent:
    """Normalised Stripe event ready for handler dispatch."""

    id: str
    type: str
    data_object: Mapping[str, Any]
    created: int


EventHandler = Callable[[StripeEvent], None]


@dataclass
class StripeWebhookDispatcher:
    """Verify + dispatch webhook posts to per-event-type handlers.

    Unknown event types are silently ignored (Stripe sends many we
    don't care about). Duplicate dispatch is suppressed via the
    ``_seen`` event-id set so retries are idempotent.
    """

    secret: str
    tolerance_s: int = 300
    _handlers: dict[str, list[EventHandler]] = field(default_factory=dict)
    _seen: set[str] = field(default_factory=set)

    def on(self, event_type: str, handler: EventHandler) -> None:
        if not event_type:
            raise StripeWebhookError("empty event type")
        self._handlers.setdefault(event_type, []).append(handler)

    def dispatch(
        self,
        *,
        payload: bytes,
        header: str,
        now_ms: int,
    ) -> StripeEvent | None:
        verify_signature(
            payload=payload,
            header=header,
            secret=self.secret,
            now_ms=now_ms,
            tolerance_s=self.tolerance_s,
        )
        try:
            body = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise StripeWebhookError("payload is not valid JSON") from exc
        event_id = body.get("id")
        event_type = body.get("type")
        if not isinstance(event_id, str) or not isinstance(event_type, str):
            raise StripeWebhookError("event missing id or type")
        if event_id in self._seen:
            return None
        data = body.get("data") or {}
        obj = data.get("object") or {}
        if not isinstance(obj, dict):
            raise StripeWebhookError("event.data.object is not an object")
        event = StripeEvent(
            id=event_id,
            type=event_type,
            data_object=obj,
            created=int(body.get("created") or (now_ms // 1000)),
        )
        self._seen.add(event_id)
        for handler in self._handlers.get(event_type, ()):
            handler(event)
        return event


# ---------------------------------------------------------------------------
# Stock handlers for the events the control plane cares about (S323/S324).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubscriptionChange:
    customer_id: str
    subscription_id: str
    status: str  # active|trialing|canceled|past_due|unpaid|incomplete...
    plan_id: str | None


@dataclass(frozen=True)
class InvoiceOutcome:
    customer_id: str
    invoice_id: str
    paid: bool
    amount_paid_micro: int  # micro-USD for parity with cost_rollup
    attempt_count: int


def parse_subscription_event(event: StripeEvent) -> SubscriptionChange:
    obj = event.data_object
    items = obj.get("items") or {}
    plan_id: str | None = None
    if isinstance(items, dict):
        data = items.get("data") or []
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict):
                price = first.get("price") or {}
                if isinstance(price, dict):
                    raw = price.get("id")
                    if isinstance(raw, str):
                        plan_id = raw
    customer = obj.get("customer")
    sub_id = obj.get("id")
    status = obj.get("status")
    if not (
        isinstance(customer, str)
        and isinstance(sub_id, str)
        and isinstance(status, str)
    ):
        raise StripeWebhookError("subscription event missing customer/id/status")
    return SubscriptionChange(
        customer_id=customer,
        subscription_id=sub_id,
        status=status,
        plan_id=plan_id,
    )


def parse_invoice_event(event: StripeEvent) -> InvoiceOutcome:
    obj = event.data_object
    customer = obj.get("customer")
    invoice_id = obj.get("id")
    if not (isinstance(customer, str) and isinstance(invoice_id, str)):
        raise StripeWebhookError("invoice event missing customer/id")
    # Stripe reports amounts in cents; convert to micro-USD (x10_000).
    amount_paid_cents = int(obj.get("amount_paid") or 0)
    paid = bool(obj.get("paid"))
    attempt = int(obj.get("attempt_count") or 0)
    return InvoiceOutcome(
        customer_id=customer,
        invoice_id=invoice_id,
        paid=paid,
        amount_paid_micro=amount_paid_cents * 10_000,
        attempt_count=attempt,
    )


def now_ms_clock() -> int:
    return int(time.time() * 1000)


__all__ = [
    "EventHandler",
    "InvoiceOutcome",
    "StripeEvent",
    "StripeWebhookDispatcher",
    "StripeWebhookError",
    "SubscriptionChange",
    "now_ms_clock",
    "parse_invoice_event",
    "parse_subscription_event",
    "verify_signature",
]
