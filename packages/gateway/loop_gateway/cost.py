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
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_EVEN, Decimal, getcontext

from loop_gateway.model_catalog import Profile, Vendor, classify_tier, vendor_for

# Bump the Decimal arithmetic precision a little above default so cost
# computation across the full token-count range (up to ~10^7 tokens)
# stays exact through the markup multiplication. The default 28 is
# already enough; we set it explicitly here so a change elsewhere in
# the process can't silently degrade billing accuracy.
getcontext().prec = 28

# Provider-disclosed markup applied on top of pass-through cost.
DISCLOSED_MARKUP_PCT = 5.0


@dataclass(frozen=True, slots=True)
class ModelRate:
    """Pricing for a single model, in USD per 1M tokens."""

    input_per_million: float
    output_per_million: float
    source_url: str


# Rates current as of 2026-04. Update with the provider's pricing page URL.
COST_TABLE_REFRESHED_AT = "2026-04-01"


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


@dataclass(frozen=True, slots=True)
class CostTableHealth:
    """Freshness status for the static pricing table."""

    refreshed_at: date
    age_days: int
    max_age_days: int
    stale_models: tuple[str, ...]

    @property
    def is_stale(self) -> bool:
        return bool(self.stale_models)


def _parse_refreshed_at(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("COST_TABLE_REFRESHED_AT must use YYYY-MM-DD format") from exc


def cost_health_check(
    *,
    today: date | None = None,
    max_age_days: int = 90,
) -> CostTableHealth:
    """Return whether the static cost table is past its freshness budget.

    ``COST_TABLE_REFRESHED_AT`` is table-level because the current table is
    maintained as one citation-bearing bundle. When it goes stale, every row
    needs a pricing-page review before we trust billing estimates again.
    """
    if max_age_days < 0:
        raise ValueError("max_age_days must be non-negative")
    refreshed_at = _parse_refreshed_at(COST_TABLE_REFRESHED_AT)
    today = today or datetime.now(UTC).date()
    age_days = (today - refreshed_at).days
    stale_models = tuple(sorted(COST_TABLE)) if age_days > max_age_days else ()
    return CostTableHealth(
        refreshed_at=refreshed_at,
        age_days=age_days,
        max_age_days=max_age_days,
        stale_models=stale_models,
    )


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


_PER_MILLION = Decimal(1_000_000)
_BILLING_QUANT = Decimal("0.00001")  # 5 decimal places (ADR-028)


def cost_for_decimal(
    model: str, input_tokens: int, output_tokens: int
) -> Decimal:
    """Pass-through cost in :class:`Decimal` USD (no markup).

    Closes vega #2 (block-prod): provider hot paths used to multiply
    floats (rate * tokens / 1_000_000), accumulating IEEE-754 rounding
    errors that showed up as ±1¢ drift between dp's metered cost and
    the cp billing reconciler. Internal arithmetic is now exact via
    Decimal; the float boundary is preserved at the wire surface
    where the GatewayDone event is serialised.
    """
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("token counts must be non-negative")
    rate = _resolve_rate(model)
    if rate is None:
        raise KeyError(f"unknown model: {model!r}")
    # ``Decimal(str(...))`` is the canonical way to introduce a float
    # rate without binary-precision contamination. The rates come from
    # citation-bearing pricing pages typed as Python floats — going
    # through ``str`` keeps the literal value intact.
    in_rate = Decimal(str(rate.input_per_million))
    out_rate = Decimal(str(rate.output_per_million))
    return (
        Decimal(input_tokens) * in_rate / _PER_MILLION
        + Decimal(output_tokens) * out_rate / _PER_MILLION
    )


def with_markup_decimal(
    pass_through_usd: Decimal | float,
    markup_pct: float = DISCLOSED_MARKUP_PCT,
) -> Decimal:
    """Apply the disclosed markup, returning :class:`Decimal` quantised
    to 5 decimal places (ADR-028).

    Accepts a Decimal or a float pass-through; the float path goes
    through ``str`` to avoid binary-precision contamination, matching
    :func:`cost_for_decimal`.
    """
    if isinstance(pass_through_usd, Decimal):
        base = pass_through_usd
    else:
        if pass_through_usd < 0:
            raise ValueError("pass-through cost must be non-negative")
        base = Decimal(str(pass_through_usd))
    if base < 0:
        raise ValueError("pass-through cost must be non-negative")
    multiplier = Decimal(1) + Decimal(str(markup_pct)) / Decimal(100)
    return (base * multiplier).quantize(_BILLING_QUANT, rounding=ROUND_HALF_EVEN)


def cost_for(model: str, input_tokens: int, output_tokens: int) -> float:
    """Pass-through cost (no markup) — float façade over
    :func:`cost_for_decimal`.

    Resolution order: exact match in :data:`COST_TABLE` first, then a
    tier-default rate if the id looks like a supported vendor. Raises
    ``KeyError`` only when both fail (e.g. a Mistral / Gemini id we
    don't have a hand-bound entry for).

    The internal computation runs in :class:`Decimal` so accumulating
    a turn's worth of token costs produces a deterministic answer; the
    return value is converted to float at the boundary because the
    wire shape (``GatewayDone.cost_usd: float``) hasn't changed.
    """
    return float(cost_for_decimal(model, input_tokens, output_tokens))


def with_markup(pass_through_usd: float, markup_pct: float = DISCLOSED_MARKUP_PCT) -> float:
    """Apply the disclosed markup. Always rounded to 5 decimals (ADR-028).

    Float façade over :func:`with_markup_decimal` for back-compat.
    """
    return float(with_markup_decimal(pass_through_usd, markup_pct))
