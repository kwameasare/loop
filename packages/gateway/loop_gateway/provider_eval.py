"""Provider evaluation suite for nightly quality/latency/cost regression checks."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ProviderEvalPrompt(_StrictModel):
    prompt_id: str
    category: str
    prompt: str
    expected_capabilities: tuple[str, ...] = ("chat",)


class ProviderRunSample(_StrictModel):
    provider: str
    prompt_id: str
    quality_score: float = Field(ge=0.0, le=1.0)
    latency_ms: int = Field(ge=0)
    cost_usd: float = Field(ge=0.0)
    ok: bool = True


class ProviderEvalReport(_StrictModel):
    provider: str
    prompts_total: int = Field(ge=0)
    prompts_ok: int = Field(ge=0)
    mean_quality: float = Field(ge=0.0, le=1.0)
    p95_latency_ms: int = Field(ge=0)
    total_cost_usd: float = Field(ge=0.0)
    passed: bool


def standard_gateway_eval_suite() -> tuple[ProviderEvalPrompt, ...]:
    """Return the 50-prompt suite used to compare provider regressions."""

    categories = (
        "tool-use",
        "memory",
        "sales",
        "support",
        "coding",
        "retrieval",
        "reasoning",
        "voice",
        "safety",
        "summarization",
    )
    prompts: list[ProviderEvalPrompt] = []
    for index in range(50):
        category = categories[index % len(categories)]
        prompts.append(
            ProviderEvalPrompt(
                prompt_id=f"gw-{index + 1:02d}",
                category=category,
                prompt=_prompt_for(category, index + 1),
                expected_capabilities=("chat", "structured-output")
                if category in {"tool-use", "coding"}
                else ("chat",),
            )
        )
    return tuple(prompts)


def summarize_provider_run(
    *,
    provider: str,
    samples: tuple[ProviderRunSample, ...],
    min_quality: float = 0.75,
    max_p95_latency_ms: int = 3_000,
    max_total_cost_usd: float = 1.00,
) -> ProviderEvalReport:
    provider_samples = tuple(sample for sample in samples if sample.provider == provider)
    if not provider_samples:
        return ProviderEvalReport(
            provider=provider,
            prompts_total=0,
            prompts_ok=0,
            mean_quality=0.0,
            p95_latency_ms=0,
            total_cost_usd=0.0,
            passed=False,
        )
    ok_samples = tuple(sample for sample in provider_samples if sample.ok)
    mean_quality = sum(sample.quality_score for sample in provider_samples) / len(provider_samples)
    latencies = sorted(sample.latency_ms for sample in provider_samples)
    p95 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]
    total_cost = round(sum(sample.cost_usd for sample in provider_samples), 6)
    return ProviderEvalReport(
        provider=provider,
        prompts_total=len(provider_samples),
        prompts_ok=len(ok_samples),
        mean_quality=round(mean_quality, 4),
        p95_latency_ms=p95,
        total_cost_usd=total_cost,
        passed=(
            len(ok_samples) == len(provider_samples)
            and mean_quality >= min_quality
            and p95 <= max_p95_latency_ms
            and total_cost <= max_total_cost_usd
        ),
    )


def _prompt_for(category: str, number: int) -> str:
    return (
        f"Eval {number}: solve a Loop {category} task with concise reasoning, "
        "clear assumptions, and a machine-readable final action."
    )


__all__ = [
    "ProviderEvalPrompt",
    "ProviderEvalReport",
    "ProviderRunSample",
    "standard_gateway_eval_suite",
    "summarize_provider_run",
]
