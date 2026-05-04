"""TurnExecutionError subclass-hierarchy tests (vega #6).

The route layer in ``runtime_app.py`` previously caught every turn
failure as a generic ``TurnExecutionError`` and returned
``LOOP-RT-501``. That meant auth failures, budget rejections, and
gateway 5xx all looked identical to clients + metrics + alerts.

This test asserts the new subclasses each carry the right
(error-code, http-status) pair so the route layer can fan out the
envelope appropriately, and that the inheritance chain still allows
a coarse ``except TurnExecutionError`` catch-all when callers don't
care about the distinction.
"""

from __future__ import annotations

import pytest
from loop_data_plane._turns import (
    TurnAuthError,
    TurnBudgetError,
    TurnExecutionError,
    TurnGatewayError,
    TurnInternalError,
    TurnRateLimitedError,
)


def test_every_subclass_inherits_from_turn_execution_error() -> None:
    """A coarse ``except TurnExecutionError`` must still catch every
    subclass — that's the whole point of preserving the base. If a
    new subclass forgets to inherit, this test fails before it ships."""
    for cls in (
        TurnAuthError,
        TurnBudgetError,
        TurnRateLimitedError,
        TurnGatewayError,
        TurnInternalError,
    ):
        assert issubclass(cls, TurnExecutionError), cls


def test_codes_are_distinct() -> None:
    """Two subclasses sharing a code would defeat the purpose of the
    hierarchy — alerts + metrics + envelopes wouldn't be able to tell
    them apart."""
    codes = [
        TurnAuthError.code,
        TurnBudgetError.code,
        TurnRateLimitedError.code,
        TurnGatewayError.code,
        TurnInternalError.code,
    ]
    assert len(codes) == len(set(codes)), f"duplicate codes: {codes}"


@pytest.mark.parametrize(
    ("cls", "code", "status"),
    [
        (TurnAuthError, "LOOP-RT-401", 401),
        (TurnBudgetError, "LOOP-RT-402", 402),
        (TurnRateLimitedError, "LOOP-RT-403", 429),
        (TurnGatewayError, "LOOP-RT-404", 502),
        (TurnInternalError, "LOOP-RT-501", 500),
    ],
)
def test_subclass_carries_expected_code_and_status(
    cls: type[TurnExecutionError], code: str, status: int
) -> None:
    """The (code, http_status) tuple is the wire contract — a typo
    here would silently break the route layer's envelope."""
    assert cls.code == code
    assert cls.http_status == status


def test_base_class_default_is_internal_error_shaped() -> None:
    """Plain ``TurnExecutionError`` (no subclass) still has the
    legacy LOOP-RT-501 / 502 default so existing call sites that
    raise the base directly don't change behaviour."""
    assert TurnExecutionError.code == "LOOP-RT-501"
    assert TurnExecutionError.http_status == 502


def test_raising_subclass_preserves_message_and_chain() -> None:
    inner = ValueError("provider rejected key")
    try:
        raise TurnAuthError("missing BYO key for workspace") from inner
    except TurnExecutionError as exc:
        assert isinstance(exc, TurnAuthError)
        assert "missing BYO key" in str(exc)
        assert exc.__cause__ is inner
        assert exc.code == "LOOP-RT-401"
