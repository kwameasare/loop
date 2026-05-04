"""Cost accounting.

The 5% disclosed margin is non-negotiable (ADR-012). Rates below are the
provider list prices in USD per 1M tokens, cited inline. When a vendor
publishes new rates, update the entry, the citation URL, and the unit tests.

Two-tier resolution
===================

1. **Exact match** in :data:`COST_TABLE` — the canonical, citation-bearing
   rate. Always preferred when available.
2. **Tier fallback** in :data:`_FALLBACK_TIER_RATES` — kicks in when the
   model id is recognisably from a supported vendor (OpenAI / Anthropic
   per :func:`loop_gateway.model_catalog.vendor_for`) but isn't yet
   bound to an exact rate. Conservative upper-bound rates; preflight
   stays pessimistic so we never undercharge.

This decoupling matters because the live model catalog discovers ids
straight from the provider's ``/v1/models`` endpoint — those ids land
in production faster than COST_TABLE entries can be hand-maintained.
The fallback keeps the runtime working without silently losing the
right to bill.
"""

from __future__ import annotations

from dataclasses import dataclass

from loop_gateway.model_catalog import Profile, Vendor, classify_tier, vendor_for

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
    # AWS Bedrock -- https://aws.amazon.com/bedrock/pricing/
    "anthropic.claude-3-5-sonnet-20240620-v1:0": ModelRate(
        3.00,
        15.00,
        "https://aws.amazon.com/bedrock/pricing/",
    ),
    "mistral.mistral-large-2402-v1:0": ModelRate(
        4.00,
        12.00,
        "https://aws.amazon.com/bedrock/pricing/",
    ),
    "meta.llama3-70b-instruct-v1:0": ModelRate(
        2.65,
        3.50,
        "https://aws.amazon.com/bedrock/pricing/",
    ),
    # Google Vertex AI -- https://cloud.google.com/vertex-ai/generative-ai/pricing
    "gemini-1.5-pro": ModelRate(
        3.50,
        10.50,
        "https://cloud.google.com/vertex-ai/generative-ai/pricing",
    ),
    "gemini-1.5-flash": ModelRate(
        0.35,
        1.05,
        "https://cloud.google.com/vertex-ai/generative-ai/pricing",
    ),
    # Mistral -- https://mistral.ai/technology/#pricing
    "mistral-large-latest": ModelRate(2.00, 6.00, "https://mistral.ai/technology/#pricing"),
    "codestral-latest": ModelRate(0.20, 0.60, "https://mistral.ai/technology/#pricing"),
    # Cohere -- https://cohere.com/pricing
    "command-r-plus": ModelRate(3.00, 15.00, "https://cohere.com/pricing"),
    "embed-english-v3.0": ModelRate(0.10, 0.00, "https://cohere.com/pricing"),
    # Groq -- https://groq.com/pricing/
    "llama-3.3-70b-versatile": ModelRate(0.59, 0.79, "https://groq.com/pricing/"),
    "qwen-2.5-32b": ModelRate(0.29, 0.39, "https://groq.com/pricing/"),
    # Self-hosted/OpenAI-compatible endpoints: local ops cost is tracked as zero.
    "vllm-local-llama": ModelRate(0.00, 0.00, "https://docs.vllm.ai/"),
    # Generic OpenAI-compatible providers.
    "together-meta-llama": ModelRate(0.90, 0.90, "https://www.together.ai/pricing"),
    "replicate-llama": ModelRate(0.65, 2.75, "https://replicate.com/pricing"),
    "fireworks-qwen": ModelRate(0.30, 0.30, "https://fireworks.ai/pricing"),
}


# Conservative tier-default rates used when a model id isn't in
# COST_TABLE but its shape matches a supported vendor. Pessimistic on
# purpose — preflight is meant to over-estimate, not under-estimate.
# Numbers track current OpenAI / Anthropic public list prices for a
# representative model in each tier (gpt-4o-mini / gpt-4o / gpt-4-turbo
# for OpenAI; haiku / sonnet / opus for Anthropic). Refresh when a
# vendor's pricing page meaningfully shifts.
_FALLBACK_CITATION = (
    "fallback-tier-rate: model id not bound to an exact rate in "
    "loop_gateway.cost.COST_TABLE; see _FALLBACK_TIER_RATES."
)
_FALLBACK_TIER_RATES: dict[tuple[Vendor, Profile], ModelRate] = {
    ("openai", "cheap"): ModelRate(0.15, 0.60, _FALLBACK_CITATION),
    ("openai", "balanced"): ModelRate(2.50, 10.00, _FALLBACK_CITATION),
    ("openai", "best"): ModelRate(15.00, 60.00, _FALLBACK_CITATION),
    ("anthropic", "cheap"): ModelRate(0.80, 4.00, _FALLBACK_CITATION),
    ("anthropic", "balanced"): ModelRate(3.00, 15.00, _FALLBACK_CITATION),
    ("anthropic", "best"): ModelRate(15.00, 75.00, _FALLBACK_CITATION),
}


def _resolve_rate(model: str) -> ModelRate | None:
    """Look up a rate, with tier-fallback for OpenAI / Anthropic ids.

    Returns ``None`` when neither lookup succeeds — the caller should
    raise ``KeyError`` to preserve the existing public contract.
    """
    if model in COST_TABLE:
        return COST_TABLE[model]
    vendor = vendor_for(model)
    if vendor is None:
        return None
    return _FALLBACK_TIER_RATES[(vendor, classify_tier(model))]


def cost_for(model: str, input_tokens: int, output_tokens: int) -> float:
    """Pass-through cost (no markup).

    Resolution order: exact match in :data:`COST_TABLE` first, then a
    tier-default rate if the id looks like a supported vendor. Raises
    ``KeyError`` only when both fail (e.g. a Mistral / Gemini id we
    don't have a hand-bound entry for).
    """
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("token counts must be non-negative")
    rate = _resolve_rate(model)
    if rate is None:
        raise KeyError(f"unknown model: {model!r}")
    return (
        input_tokens * rate.input_per_million / 1_000_000
        + output_tokens * rate.output_per_million / 1_000_000
    )


def with_markup(pass_through_usd: float, markup_pct: float = DISCLOSED_MARKUP_PCT) -> float:
    """Apply the disclosed markup. Always rounded to 5 decimals (ADR-028)."""
    if pass_through_usd < 0:
        raise ValueError("pass-through cost must be non-negative")
    return round(pass_through_usd * (1 + markup_pct / 100), 5)
