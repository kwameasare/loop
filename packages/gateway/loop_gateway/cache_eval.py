"""Fixed gateway semantic-cache eval workload for S841."""

from __future__ import annotations

from dataclasses import dataclass

from loop_gateway.semantic_cache import SemanticCache

MIN_HIT_RATIO = 0.30

WORKLOAD: tuple[tuple[str, str], ...] = (
    ("What is the refund policy for annual plans?", "Refunds are prorated for 30 days."),
    ("How do annual plan refunds work?", "Refunds are prorated for 30 days."),
    ("What is the refund policy for annual plans?", "Refunds are prorated for 30 days."),
    ("Show my current usage limit.", "Usage limits are listed in Settings."),
    ("Where can I find my usage limit?", "Usage limits are listed in Settings."),
    ("Show my current usage limit.", "Usage limits are listed in Settings."),
    ("Reset the API key for workspace alpha.", "Open Settings and rotate the API key."),
    ("Reset the API key for workspace alpha.", "Open Settings and rotate the API key."),
    ("Why is the Slack channel disconnected?", "Reconnect OAuth from Channels."),
    ("Why is the Slack channel disconnected?", "Reconnect OAuth from Channels."),
)

VOCAB = (
    "refund",
    "annual",
    "usage",
    "limit",
    "api",
    "key",
    "slack",
    "disconnected",
)


@dataclass(frozen=True, slots=True)
class GatewayCacheEvalResult:
    requests: int
    hits: int
    misses: int
    hit_ratio: float
    min_hit_ratio: float
    passed: bool

    def as_dict(self) -> dict[str, int | float | bool | str]:
        return {
            "name": "gateway_cache_hit_ratio_fixed_eval",
            "requests": self.requests,
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": self.hit_ratio,
            "min_hit_ratio": self.min_hit_ratio,
            "passed": self.passed,
        }


async def _embed(prompt: str) -> list[float]:
    normalized = prompt.lower()
    return [float(normalized.count(term)) for term in VOCAB]


async def run_gateway_cache_eval(
    *,
    min_hit_ratio: float = MIN_HIT_RATIO,
    cache_threshold: float = 0.97,
) -> GatewayCacheEvalResult:
    if not 0.0 <= min_hit_ratio <= 1.0:
        raise ValueError("min_hit_ratio must be in [0, 1]")
    cache = SemanticCache(_embed, threshold=cache_threshold, ttl_seconds=3600)
    hits = 0
    misses = 0
    for prompt, response in WORKLOAD:
        hit = await cache.lookup(workspace_id="gateway-cache-eval", prompt=prompt)
        if hit is None:
            misses += 1
            await cache.store(workspace_id="gateway-cache-eval", prompt=prompt, response=response)
        else:
            hits += 1
    requests = hits + misses
    hit_ratio = round(hits / requests, 4)
    return GatewayCacheEvalResult(
        requests=requests,
        hits=hits,
        misses=misses,
        hit_ratio=hit_ratio,
        min_hit_ratio=min_hit_ratio,
        passed=hit_ratio >= min_hit_ratio,
    )
