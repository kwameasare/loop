"""Tests for the WhatsApp 24-hour window enforcer (S345)."""

from __future__ import annotations

import pytest
from loop_channels_whatsapp.window import (
    WINDOW_MS,
    OutsideWindowError,
    WindowTracker,
)


def test_no_inbound_means_window_closed() -> None:
    tracker = WindowTracker()
    state = tracker.state("+1555", now_ms=10_000)
    assert state.open is False
    assert state.elapsed_ms == -1


def test_inbound_opens_window_for_24h() -> None:
    tracker = WindowTracker()
    tracker.record_inbound("+1555", now_ms=0)
    assert tracker.state("+1555", now_ms=WINDOW_MS).open is True
    assert tracker.state("+1555", now_ms=WINDOW_MS + 1).open is False


def test_template_outbound_always_passes() -> None:
    tracker = WindowTracker()
    # No inbound at all — template still allowed.
    state = tracker.check_outbound("+1555", kind="template", now_ms=10_000)
    assert state.open is False


def test_free_form_after_window_raises() -> None:
    tracker = WindowTracker()
    tracker.record_inbound("+1555", now_ms=0)
    with pytest.raises(OutsideWindowError) as exc:
        tracker.check_outbound(
            "+1555", kind="free_form", now_ms=WINDOW_MS + 1000
        )
    assert exc.value.phone == "+1555"
    assert exc.value.elapsed_ms > WINDOW_MS


def test_record_inbound_keeps_latest() -> None:
    tracker = WindowTracker()
    tracker.record_inbound("+1555", now_ms=1000)
    # Older inbound must not regress the window.
    tracker.record_inbound("+1555", now_ms=500)
    state = tracker.state("+1555", now_ms=WINDOW_MS + 999)
    # If 1000 was kept (correct), elapsed at WINDOW_MS+999 = WINDOW_MS-1 (open).
    assert state.open is True
    assert state.elapsed_ms == WINDOW_MS - 1
