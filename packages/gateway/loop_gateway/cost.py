"""Cost accounting.

The 5% disclosed margin is non-negotiable (ADR-012). Rates below are the
provider list prices in USD per 1M tokens, cited inline. When a vendor
publishes new rates, update the entry, the citation URL, and the unit tests.
"""

from __future__ import annotations

from dataclasses import dataclass

# Provider-disclosed markup applied on top of pass-through cost.
DISCLOSED_MARKUP_PCT = 5.0


@dataclass(frozen=True, slots=True)
class ModelRate:
    """Pricing for a single model, in USD per 1M tokens."""

    input_per_million: float
    output_per_million: float
    source_url: str


# Rates current as of 2026-04. Update with the provider's pricing page URL.
COST_TABLE: dict[str, ModelRate] = {
    # OpenAI -- https://openai.com/api/pricing/
    "gpt-4o-mini": ModelRate(0.15, 0.60, "https://openai.com/api/pricing/"),
    "gpt-4o": ModelRate(2.50, 10.00, "https://openai.com/api/pricing/"),
    # Anthropic -- https://www.anthropic.com/pricing
    "claude-3-5-haiku": ModelRate(0.80, 4.00, "https://www.anthropic.com/pricing"),
    "claude-3-5-sonnet": ModelRate(3.00, 15.00, "https://www.anthropic.com/pricing"),
}


def cost_for(model: str, input_tokens: int, output_tokens: int) -> float:
    """Pass-through cost (no markup)."""
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("token counts must be non-negative")
    if model not in COST_TABLE:
        raise KeyError(f"unknown model: {model!r}")
    rate = COST_TABLE[model]
    return (
        input_tokens * rate.input_per_million / 1_000_000
        + output_tokens * rate.output_per_million / 1_000_000
    )


def with_markup(pass_through_usd: float, markup_pct: float = DISCLOSED_MARKUP_PCT) -> float:
    """Apply the disclosed markup. Always rounded to 5 decimals (ADR-028)."""
    if pass_through_usd < 0:
        raise ValueError("pass-through cost must be non-negative")
    return round(pass_through_usd * (1 + markup_pct / 100), 5)
