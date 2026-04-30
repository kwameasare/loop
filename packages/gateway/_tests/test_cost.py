"""Unit tests for cost.py: pass-through math, 5% markup, error paths."""

from __future__ import annotations

import math

import pytest
from loop_gateway.cost import COST_TABLE, DISCLOSED_MARKUP_PCT, cost_for, with_markup


def test_cost_for_known_model_uses_published_rate() -> None:
    # gpt-4o: $2.50 / 1M input + $10.00 / 1M output.
    cost = cost_for("gpt-4o", input_tokens=1_000_000, output_tokens=1_000_000)
    assert math.isclose(cost, 12.50, rel_tol=1e-9)


def test_cost_for_zero_tokens_is_zero() -> None:
    assert cost_for("claude-3-5-haiku", 0, 0) == 0.0


def test_cost_for_unknown_model_raises() -> None:
    with pytest.raises(KeyError):
        cost_for("does-not-exist", 100, 100)


def test_cost_for_negative_tokens_raises() -> None:
    with pytest.raises(ValueError):
        cost_for("gpt-4o-mini", -1, 0)


def test_with_markup_applies_disclosed_5_percent() -> None:
    assert with_markup(1.0) == 1.05
    assert with_markup(0.0) == 0.0
    assert DISCLOSED_MARKUP_PCT == 5.0


def test_with_markup_rejects_negative() -> None:
    with pytest.raises(ValueError):
        with_markup(-0.01)


def test_every_model_in_table_has_source_url() -> None:
    # If a rate ever ships without a citation, the audit trail breaks.
    for name, rate in COST_TABLE.items():
        assert rate.source_url.startswith("https://"), name
        assert rate.input_per_million >= 0
        assert rate.output_per_million >= 0
