"""Budget pre-flight: estimate cost BEFORE we call upstream.

The runtime consults :func:`preflight_budget` at the start of every
iteration. The verdict is one of:

- ``"allow"`` -- estimated cost fits in the remaining budget; proceed.
- ``"swap"`` -- the estimate would exceed the cap on the requested model
  but a cheaper ``fallback_model`` would fit; the caller should switch
  models for this iteration and emit a ``degrade`` event explaining why.
- ``"deny"`` -- even the fallback would not fit (or no fallback was
  configured); the caller should emit ``degrade`` and end the turn.

Pre-flight is intentionally pessimistic: we use the model's per-token
**output** rate for the entire ``max_output_tokens`` budget, because
that's the worst case if the model emits a full-length response.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from loop_gateway.cost import cost_for

Verdict = Literal["allow", "swap", "deny"]


class BudgetCheck(BaseModel):
    """Result of a budget pre-flight."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    verdict: Verdict
    model: str
    estimated_cost_usd: float = Field(ge=0.0)
    remaining_usd: float = Field(ge=0.0)
    reason: str = ""


def estimate_upper_bound_cost(
    model: str,
    *,
    input_tokens: int,
    max_output_tokens: int,
) -> float:
    """Worst-case pass-through cost for an iteration.

    Delegates rate resolution to :func:`loop_gateway.cost.cost_for`,
    which prefers the exact-match :data:`~loop_gateway.cost.COST_TABLE`
    entry and falls back to a tier-default rate for OpenAI / Anthropic
    ids the live catalog discovered but we haven't bound to an exact
    rate yet. ``KeyError`` only fires when both lookups fail (i.e. an
    id we genuinely can't price — typically a non-OpenAI / non-Anthropic
    vendor that hasn't been hand-added to the table).
    """

    if input_tokens < 0 or max_output_tokens < 0:
        raise ValueError("token counts must be non-negative")
    return cost_for(model, input_tokens, max_output_tokens)


def preflight_budget(
    *,
    model: str,
    input_tokens: int,
    max_output_tokens: int,
    remaining_usd: float,
    fallback_model: str | None = None,
) -> BudgetCheck:
    """Decide whether the next iteration fits in the remaining budget.

    Determinism: the same inputs always return the same verdict. Callers
    that retry the same request (same ``request_id``) will land on the
    same side of every threshold.
    """

    if remaining_usd < 0:
        raise ValueError("remaining_usd must be non-negative")

    primary_cost = estimate_upper_bound_cost(
        model, input_tokens=input_tokens, max_output_tokens=max_output_tokens
    )
    if primary_cost <= remaining_usd:
        return BudgetCheck(
            verdict="allow",
            model=model,
            estimated_cost_usd=primary_cost,
            remaining_usd=remaining_usd,
        )

    if fallback_model is not None and fallback_model != model:
        fallback_cost = estimate_upper_bound_cost(
            fallback_model,
            input_tokens=input_tokens,
            max_output_tokens=max_output_tokens,
        )
        if fallback_cost <= remaining_usd:
            return BudgetCheck(
                verdict="swap",
                model=fallback_model,
                estimated_cost_usd=fallback_cost,
                remaining_usd=remaining_usd,
                reason=(
                    f"primary {model!r} estimate ${primary_cost:.5f} "
                    f"exceeds remaining ${remaining_usd:.5f}; falling "
                    f"back to {fallback_model!r}"
                ),
            )

    return BudgetCheck(
        verdict="deny",
        model=model,
        estimated_cost_usd=primary_cost,
        remaining_usd=remaining_usd,
        reason=(
            f"estimate ${primary_cost:.5f} exceeds remaining "
            f"${remaining_usd:.5f}; no fallback fits"
        ),
    )


__all__ = [
    "BudgetCheck",
    "Verdict",
    "estimate_upper_bound_cost",
    "preflight_budget",
]
