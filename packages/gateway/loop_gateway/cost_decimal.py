"""Decimal-based cost arithmetic (S713, extends ADR-028).

The legacy float-based API in ``cost.py`` rounded to 5 decimals which
loses sub-cent precision once a workspace's monthly bill crosses ~10$
(IEEE-754 round-half-to-even drift). This module ships a parallel
Decimal API used by the rollup path \u2014 ``cost.py`` keeps the float
helpers for back-compat (existing call sites, existing tests) and
delegates to here when exactness matters.

Quantum: 7 decimal places (``0.0000001``). That covers per-token billing
for any model in the COST_TABLE without surfacing scientific-notation
rounding to invoices.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, getcontext

from loop_gateway.cost import COST_TABLE, DISCLOSED_MARKUP_PCT, _resolve_rate

#: 7 decimal-place quantum used for all internal Decimal math.
COST_QUANTUM: Decimal = Decimal("0.0000001")
#: Global Decimal precision: 28 significant digits is the Python default
#: but we make it explicit so a caller setting a sloppy context doesn't
#: silently corrupt invoices.
_DECIMAL_PRECISION: int = 28


def _ensure_precision() -> None:
    if getcontext().prec < _DECIMAL_PRECISION:
        getcontext().prec = _DECIMAL_PRECISION


def _rate_decimal(model: str, *, output: bool) -> Decimal:
    rate = _resolve_rate(model)
    if rate is None:
        raise KeyError(f"unknown model: {model!r}")
    raw = rate.output_per_million if output else rate.input_per_million
    # Convert via str() so we don't carry float artefacts into Decimal.
    return Decimal(str(raw))


def cost_for_decimal(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    """Pass-through cost as Decimal, quantised to ``COST_QUANTUM``."""
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("token counts must be non-negative")
    _ensure_precision()
    one_million = Decimal(1_000_000)
    in_cost = Decimal(input_tokens) * _rate_decimal(model, output=False) / one_million
    out_cost = Decimal(output_tokens) * _rate_decimal(model, output=True) / one_million
    total = in_cost + out_cost
    return total.quantize(COST_QUANTUM, rounding=ROUND_HALF_EVEN)


def with_markup_decimal(
    pass_through_usd: Decimal,
    markup_pct: float = DISCLOSED_MARKUP_PCT,
) -> Decimal:
    """Apply the disclosed markup. Quantised to ``COST_QUANTUM``."""
    if pass_through_usd < 0:
        raise ValueError("pass-through cost must be non-negative")
    if markup_pct < 0:
        raise ValueError("markup_pct must be non-negative")
    _ensure_precision()
    factor = Decimal(1) + Decimal(str(markup_pct)) / Decimal(100)
    return (pass_through_usd * factor).quantize(COST_QUANTUM, rounding=ROUND_HALF_EVEN)


def sum_costs(values: list[Decimal]) -> Decimal:
    """Sum a list of ``Decimal`` costs without losing the quantum.

    Used by the cost-rollup path \u2014 summing thousands of float costs
    accumulates 1e-15 drift, which then surfaces as 1-cent-off invoices
    once you scale to 1M+ requests/month.
    """
    _ensure_precision()
    total = Decimal(0)
    for v in values:
        if v < 0:
            raise ValueError("cost values must be non-negative")
        total += v
    return total.quantize(COST_QUANTUM, rounding=ROUND_HALF_EVEN)


def to_invoice_amount(value: Decimal) -> Decimal:
    """Round a Decimal cost to 2 decimals (invoice presentation)."""
    if value < 0:
        raise ValueError("invoice amount must be non-negative")
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


__all__ = [
    "COST_QUANTUM",
    "cost_for_decimal",
    "sum_costs",
    "to_invoice_amount",
    "with_markup_decimal",
]
