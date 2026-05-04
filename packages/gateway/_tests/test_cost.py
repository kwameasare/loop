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


def test_cost_for_unknown_vendor_raises() -> None:
    """Ids that don't match a supported vendor prefix still raise.
    Tier fallback only applies to OpenAI- / Anthropic-shaped ids."""
    with pytest.raises(KeyError):
        cost_for("does-not-exist", 100, 100)
    with pytest.raises(KeyError):
        cost_for("mistral-fake-model", 100, 100)


def test_cost_for_discovered_openai_model_uses_tier_fallback() -> None:
    """Regression for the live-catalog → cost-table coupling: a model id
    discovered from OpenAI's ``/v1/models`` (e.g. ``gpt-5.4-mini``) that
    isn't yet bound to an exact rate now resolves via tier fallback
    rather than raising. Cheap-tier rate matches gpt-4o-mini's."""
    discovered = cost_for("gpt-5.4-mini", 1_000_000, 0)
    catalogued = cost_for("gpt-4o-mini", 1_000_000, 0)
    assert discovered == pytest.approx(catalogued)


def test_cost_for_discovered_pro_model_uses_best_tier_fallback() -> None:
    """Frontier id resolves to a high-rate fallback so we don't
    undercharge for premium output."""
    pro_cost = cost_for("gpt-5.5-pro-2026-04-23", 0, 1_000_000)
    mini_cost = cost_for("gpt-5.4-mini", 0, 1_000_000)
    # Best tier ($60/M out) vs cheap tier ($0.60/M out) — 100x apart.
    assert pro_cost > mini_cost * 50


def test_cost_for_discovered_claude_model_uses_anthropic_fallback() -> None:
    """Anthropic-shaped discovered ids hit anthropic-tier fallbacks."""
    haiku_new = cost_for("claude-haiku-4-5-20251001", 1_000_000, 0)
    haiku_old = cost_for("claude-3-5-haiku", 1_000_000, 0)
    assert haiku_new == pytest.approx(haiku_old)


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
