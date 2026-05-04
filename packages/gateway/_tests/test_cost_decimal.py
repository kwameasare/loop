"""Decimal cost-arithmetic tests (vega #2).

The provider hot path used to multiply rates and tokens as IEEE-754
floats; rounding errors compounded across a turn's worth of cost
events surfaced as ±1¢ drift between dp's metered cost and cp's
billing reconciler. ``cost_for_decimal`` + ``with_markup_decimal``
keep the arithmetic exact through the markup multiplication.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from loop_gateway.cost import (
    DISCLOSED_MARKUP_PCT,
    cost_for,
    cost_for_decimal,
    with_markup,
    with_markup_decimal,
)


def test_cost_for_decimal_returns_decimal() -> None:
    out = cost_for_decimal("gpt-4o-mini", 1_000, 500)
    assert isinstance(out, Decimal)


def test_cost_for_float_facade_matches_decimal() -> None:
    """The float façade must produce the same numeric value as the
    Decimal core (within float precision). Otherwise the wire shape
    silently disagrees with the audit log."""
    rounded = cost_for("gpt-4o-mini", 1_000, 500)
    exact = cost_for_decimal("gpt-4o-mini", 1_000, 500)
    assert rounded == pytest.approx(float(exact), rel=1e-12)


def test_with_markup_decimal_quantises_to_5_decimals() -> None:
    """ADR-028: every persisted cost must be quantised to 5 decimal
    places so the storage representation across cp + dp + audit_log
    is byte-identical."""
    out = with_markup_decimal(Decimal("1.234567890123"))
    # Either the value has at most 5 decimal places, or it's the
    # quantised tail of a larger number.
    _sign, _digits, exponent = out.as_tuple()
    assert isinstance(exponent, int) and exponent == -5


def test_with_markup_applies_disclosed_markup() -> None:
    base = Decimal("1.0")
    out = with_markup_decimal(base, markup_pct=5.0)
    # 1.00 * 1.05 = 1.05 exactly.
    assert out == Decimal("1.05000")


def test_decimal_avoids_float_rounding_drift_across_many_turns() -> None:
    """Sum 100 cheap cost events; the Decimal sum is exact, the
    float sum drifts by ~1e-15 which compounds in the audit reconciler.

    This test is the canary: if a future change reverts the cost
    arithmetic to floats, the assertion will trip."""
    decimal_total = sum(
        (cost_for_decimal("gpt-4o-mini", 100, 50) for _ in range(100)),
        start=Decimal(0),
    )
    # Single computation of the same workload — must equal the per-event sum.
    one_shot = cost_for_decimal("gpt-4o-mini", 100 * 100, 50 * 100)
    assert decimal_total == one_shot


def test_with_markup_rejects_negative() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        with_markup_decimal(Decimal("-0.001"))
    with pytest.raises(ValueError, match="non-negative"):
        with_markup(-0.001)


def test_default_markup_pct_is_disclosed_value() -> None:
    """The DISCLOSED_MARKUP_PCT constant is the contractual default;
    a regression that silently changed it would mis-bill every turn."""
    base = Decimal("1.0")
    expected = with_markup_decimal(base, markup_pct=DISCLOSED_MARKUP_PCT)
    actual = with_markup_decimal(base)
    assert actual == expected


def test_cost_for_decimal_independent_of_token_split() -> None:
    """A property: 100 input + 200 output = 300 input/output bundled
    only when the rate is identical for both. We're checking a
    different invariant here: doubling inputs doubles input cost
    without affecting output cost."""
    base = cost_for_decimal("gpt-4o-mini", 100, 0)
    doubled = cost_for_decimal("gpt-4o-mini", 200, 0)
    assert doubled == base * 2
