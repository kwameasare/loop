"""WhatsApp 24-hour customer-care window enforcement (S345).

Meta's policy: a business may send free-form messages to a user only
within 24 hours of the user's most recent inbound message. Outside
that window, the only legal outbound is an approved Message Template.

The runtime must reject free-form attempts before they hit the WA
Cloud API (which would 400 anyway) and emit a helpful error so the
agent author knows to switch to a template.

Surface
-------

* ``WindowState`` — frozen dataclass, ``open|closed`` + ``elapsed_ms``.
* ``WindowTracker.record_inbound(phone, now_ms)`` — opens the window.
* ``WindowTracker.check_outbound(phone, kind, now_ms)`` — raises
  ``OutsideWindowError`` if ``kind == "free_form"`` and the window is
  closed; ``kind == "template"`` always passes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

OutboundKind = Literal["free_form", "template"]

# Meta-published window length. Exported so callers can express
# policies relative to it without re-typing the magic number.
WINDOW_MS: int = 24 * 60 * 60 * 1000


class OutsideWindowError(RuntimeError):
    """Raised on a free-form outbound after the 24h window closed."""

    def __init__(self, phone: str, elapsed_ms: int) -> None:
        super().__init__(
            f"WhatsApp 24h window closed for {phone} "
            f"({elapsed_ms}ms since last inbound); use a template message"
        )
        self.phone = phone
        self.elapsed_ms = elapsed_ms


@dataclass(frozen=True)
class WindowState:
    open: bool
    elapsed_ms: int  # ms since most recent inbound; -1 if no inbound yet


@dataclass
class WindowTracker:
    """Per-phone last-inbound clock, in-process.

    Production wires the same surface against ``conversations.last_user_message_at``
    so the answer survives restart; tests use the dict.
    """

    _last_inbound_ms: dict[str, int] = field(default_factory=dict)

    def record_inbound(self, phone: str, *, now_ms: int) -> None:
        if not phone:
            raise ValueError("phone must be non-empty")
        # Latest wins — never reopen with an older timestamp.
        prev = self._last_inbound_ms.get(phone, -1)
        if now_ms > prev:
            self._last_inbound_ms[phone] = now_ms

    def state(self, phone: str, *, now_ms: int) -> WindowState:
        last = self._last_inbound_ms.get(phone, -1)
        if last < 0:
            return WindowState(open=False, elapsed_ms=-1)
        elapsed = now_ms - last
        return WindowState(open=elapsed <= WINDOW_MS, elapsed_ms=elapsed)

    def check_outbound(
        self,
        phone: str,
        *,
        kind: OutboundKind,
        now_ms: int,
    ) -> WindowState:
        state = self.state(phone, now_ms=now_ms)
        if kind == "template":
            return state
        if not state.open:
            raise OutsideWindowError(phone, state.elapsed_ms)
        return state


__all__ = [
    "WINDOW_MS",
    "OutboundKind",
    "OutsideWindowError",
    "WindowState",
    "WindowTracker",
]
