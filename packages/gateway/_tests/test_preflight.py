"""Tests for loop_gateway.preflight."""

from __future__ import annotations

import pytest
from loop_gateway import (
    BudgetCheck,
    estimate_upper_bound_cost,
    preflight_budget,
)


def test_estimate_upper_bound_cost_uses_output_rate() -> None:
    # gpt-4o: $2.50/1M input, $10.00/1M output (cost.py).
    cost = estimate_upper_bound_cost("gpt-4o", input_tokens=1_000, max_output_tokens=2_000)
    assert cost == pytest.approx(0.001 * 2.50 + 0.002 * 10.00)


def test_estimate_rejects_negative_tokens() -> None:
    with pytest.raises(ValueError):
        estimate_upper_bound_cost(
            "gpt-4o", input_tokens=-1, max_output_tokens=1
        )


def test_estimate_rejects_unknown_model() -> None:
    with pytest.raises(KeyError):
        estimate_upper_bound_cost(
            "gpt-9000", input_tokens=10, max_output_tokens=10
        )


def test_preflight_allows_when_under_budget() -> None:
    check = preflight_budget(
        model="gpt-4o-mini",
        input_tokens=500,
        max_output_tokens=500,
        remaining_usd=1.00,
    )
    assert check.verdict == "allow"
    assert check.model == "gpt-4o-mini"
    assert check.estimated_cost_usd > 0
    assert check.estimated_cost_usd <= 1.00


def test_preflight_swaps_to_fallback_when_primary_too_expensive() -> None:
    # gpt-4o output rate is 10x gpt-4o-mini's; with a tight budget,
    # primary should be rejected and the cheaper fallback chosen.
    check = preflight_budget(
        model="gpt-4o",
        input_tokens=10_000,
        max_output_tokens=10_000,
        remaining_usd=0.05,
        fallback_model="gpt-4o-mini",
    )
    assert check.verdict == "swap"
    assert check.model == "gpt-4o-mini"
    assert check.estimated_cost_usd <= 0.05
    assert "fallback" in check.reason.lower() or "falling back" in check.reason.lower()


def test_preflight_denies_when_no_fallback_fits() -> None:
    check = preflight_budget(
        model="gpt-4o",
        input_tokens=10_000,
        max_output_tokens=10_000,
        remaining_usd=0.0,
    )
    assert check.verdict == "deny"
    assert "exceeds remaining" in check.reason


def test_preflight_denies_when_fallback_also_too_expensive() -> None:
    check = preflight_budget(
        model="gpt-4o",
        input_tokens=1_000_000,
        max_output_tokens=1_000_000,
        remaining_usd=0.10,
        fallback_model="gpt-4o-mini",
    )
    assert check.verdict == "deny"


def test_preflight_is_deterministic() -> None:
    kwargs: dict[str, object] = {
        "model": "gpt-4o",
        "input_tokens": 1_000,
        "max_output_tokens": 2_000,
        "remaining_usd": 0.05,
        "fallback_model": "gpt-4o-mini",
    }
    a = preflight_budget(**kwargs)  # type: ignore[arg-type]
    b = preflight_budget(**kwargs)  # type: ignore[arg-type]
    assert a == b


def test_preflight_rejects_negative_remaining() -> None:
    with pytest.raises(ValueError):
        preflight_budget(
            model="gpt-4o",
            input_tokens=10,
            max_output_tokens=10,
            remaining_usd=-0.01,
        )


def test_budget_check_is_frozen() -> None:
    from pydantic import ValidationError

    check = BudgetCheck(
        verdict="allow",
        model="gpt-4o-mini",
        estimated_cost_usd=0.001,
        remaining_usd=1.0,
    )
    with pytest.raises(ValidationError):
        check.verdict = "deny"  # type: ignore[misc]
