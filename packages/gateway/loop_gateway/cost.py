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
