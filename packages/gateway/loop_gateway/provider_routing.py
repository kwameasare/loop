"""Provider routing, failover, and gateway-side provider rate limits."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from loop_gateway.aliases import resolve
from loop_gateway.provider_profiles import ProviderCatalog
from loop_gateway.types import GatewayError, GatewayEvent, GatewayRequest, Provider


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class RouteIntent(StrEnum):
    SMART = "smart"
    CHEAP = "cheap"
    FAST = "fast"
    QUALITY = "quality"


class ProviderCapability(StrEnum):
    CHAT = "chat"
    EMBEDDING = "embedding"


class RouteRequest(_StrictModel):
    workspace_id: str
    model: str
    intent: RouteIntent = RouteIntent.SMART
    capability: ProviderCapability = ProviderCapability.CHAT
    preferred_provider: str | None = None
    disabled_providers: tuple[str, ...] = ()
    min_quality_tier: int | None = Field(default=None, ge=1, le=5)
    max_latency_tier: int | None = Field(default=None, ge=1, le=5)
    max_cost_tier: int | None = Field(default=None, ge=1, le=5)


class ProviderScore(_StrictModel):
    provider: str
    model: str
    score: float
    reasons: tuple[str, ...]


class ProviderRoute(_StrictModel):
    provider: str
    model: str
    reason: str


class RouteDecision(_StrictModel):
    primary: ProviderRoute
    fallbacks: tuple[ProviderRoute, ...]
    scores: tuple[ProviderScore, ...]


class FailoverAttempt(_StrictModel):
    provider: str
    status: str
    code: str | None = None


class FailoverTrace(_StrictModel):
    request_id: str
    attempts: tuple[FailoverAttempt, ...]


class WorkspaceAliasResolver:
    """Default aliases plus optional per-workspace overrides."""

    def __init__(
        self,
        workspace_overrides: Mapping[str, Mapping[str, str]] | None = None,
    ) -> None:
        self._workspace_overrides = workspace_overrides or {}

    def resolve(self, *, workspace_id: str, model_or_alias: str) -> str:
        overrides = self._workspace_overrides.get(workspace_id)
        return resolve(model_or_alias, dict(overrides) if overrides is not None else None)


class ProviderRouter:
    """Select the best provider by intent and return a deterministic fallback chain."""

    def __init__(
        self,
        catalog: ProviderCatalog | None = None,
        *,
        aliases: WorkspaceAliasResolver | None = None,
    ) -> None:
        self._catalog = catalog or ProviderCatalog()
        self._aliases = aliases or WorkspaceAliasResolver()

    def route(self, request: RouteRequest) -> RouteDecision:
        model = self._aliases.resolve(
            workspace_id=request.workspace_id,
            model_or_alias=request.model,
        )
        require_embedding = request.capability is ProviderCapability.EMBEDDING
        profiles = self._catalog.eligible(model, require_embedding=require_embedding)
        disabled = set(request.disabled_providers)
        scored: list[ProviderScore] = []
        for profile in profiles:
            if profile.name in disabled:
                continue
            if request.min_quality_tier is not None and profile.quality_tier < request.min_quality_tier:
                continue
            if request.max_latency_tier is not None and profile.latency_tier > request.max_latency_tier:
                continue
            if request.max_cost_tier is not None and profile.cost_tier > request.max_cost_tier:
                continue
            score, reasons = _score_profile(request, profile.name)
            score += profile.quality_tier * 2
            score -= profile.latency_tier
            score -= profile.cost_tier
            if request.intent is RouteIntent.CHEAP:
                score -= profile.cost_tier * 3
            elif request.intent is RouteIntent.FAST:
                score -= profile.latency_tier * 4
            elif request.intent is RouteIntent.QUALITY:
                score += profile.quality_tier * 4
            scored.append(
                ProviderScore(
                    provider=profile.name,
                    model=model,
                    score=score,
                    reasons=tuple(reasons),
                )
            )
        if not scored:
            raise LookupError(f"no provider route for {request.model!r}")
        scored.sort(key=lambda item: (-item.score, item.provider))
        routes = tuple(
            ProviderRoute(provider=item.provider, model=item.model, reason=", ".join(item.reasons))
            for item in scored
        )
        return RouteDecision(primary=routes[0], fallbacks=routes[1:], scores=tuple(scored))


def _score_profile(request: RouteRequest, provider_name: str) -> tuple[float, list[str]]:
    score = 0.0
    reasons = [f"intent={request.intent.value}"]
    if request.preferred_provider == provider_name:
        score += 100.0
        reasons.append("preferred")
    if request.capability is ProviderCapability.EMBEDDING:
        reasons.append("embedding")
    return score, reasons


class ProviderRateLimitExceeded(Exception):  # noqa: N818
    code = "LOOP-GW-301"


class ProviderRateLimitConfig(_StrictModel):
    capacity: float = Field(gt=0)
    refill_per_second: float = Field(gt=0)


@dataclass(slots=True)
class _Bucket:
    tokens: float
    last_refill: float


class ProviderRateLimiter:
    """Token bucket isolated by provider, workspace, and upstream key id."""

    def __init__(
        self,
        config: ProviderRateLimitConfig,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._config = config
        self._clock = clock
        self._buckets: dict[tuple[str, str, str], _Bucket] = {}

    def acquire(
        self,
        *,
        provider: str,
        workspace_id: str,
        key_id: str,
        cost: float = 1.0,
    ) -> None:
        if cost <= 0:
            raise ValueError("cost must be positive")
        key = (provider, workspace_id, key_id)
        bucket = self._refilled_bucket(key)
        if bucket.tokens < cost:
            raise ProviderRateLimitExceeded(f"rate limit exceeded for {provider}")
        bucket.tokens -= cost

    def tokens(self, *, provider: str, workspace_id: str, key_id: str) -> float:
        return self._refilled_bucket((provider, workspace_id, key_id)).tokens

    def _refilled_bucket(self, key: tuple[str, str, str]) -> _Bucket:
        now = self._clock()
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = _Bucket(tokens=self._config.capacity, last_refill=now)
            self._buckets[key] = bucket
            return bucket
        elapsed = max(0.0, now - bucket.last_refill)
        bucket.tokens = min(
            self._config.capacity,
            bucket.tokens + elapsed * self._config.refill_per_second,
        )
        bucket.last_refill = now
        return bucket


class ProviderFailoverRunner:
    """Run a routed request, retrying the next provider after retryable failures."""

    def __init__(
        self,
        providers: Mapping[str, Provider],
        router: ProviderRouter,
        *,
        retryable_codes: tuple[str, ...] = ("GW-5XX", "GW-TIMEOUT", "GW-RATE"),
    ) -> None:
        self._providers = providers
        self._router = router
        self._retryable_codes = retryable_codes
        self.last_trace: FailoverTrace | None = None

    async def stream(
        self,
        request: GatewayRequest,
        route_request: RouteRequest,
    ) -> AsyncIterator[GatewayEvent]:
        decision = self._router.route(route_request)
        routes = (decision.primary, *decision.fallbacks)
        attempts: list[FailoverAttempt] = []
        for route in routes:
            provider = self._providers[route.provider]
            emitted_payload = False
            try:
                resolved = request.model_copy(update={"model": route.model})
                async for event in provider.stream(resolved):
                    if isinstance(event, GatewayError):
                        attempts.append(
                            FailoverAttempt(
                                provider=route.provider,
                                status="error",
                                code=event.code,
                            )
                        )
                        if event.code in self._retryable_codes and not emitted_payload:
                            break
                        self.last_trace = FailoverTrace(
                            request_id=request.request_id,
                            attempts=tuple(attempts),
                        )
                        yield event
                        return
                    emitted_payload = True
                    yield event
                else:
                    attempts.append(FailoverAttempt(provider=route.provider, status="ok"))
                    self.last_trace = FailoverTrace(
                        request_id=request.request_id,
                        attempts=tuple(attempts),
                    )
                    return
            except TimeoutError:
                attempts.append(
                    FailoverAttempt(provider=route.provider, status="error", code="GW-TIMEOUT")
                )
                continue
        self.last_trace = FailoverTrace(request_id=request.request_id, attempts=tuple(attempts))
        yield GatewayError(code="GW-FAILOVER", message="all providers failed")


__all__ = [
    "FailoverAttempt",
    "FailoverTrace",
    "ProviderCapability",
    "ProviderFailoverRunner",
    "ProviderRateLimitConfig",
    "ProviderRateLimitExceeded",
    "ProviderRateLimiter",
    "ProviderRoute",
    "ProviderRouter",
    "ProviderScore",
    "RouteDecision",
    "RouteIntent",
    "RouteRequest",
    "WorkspaceAliasResolver",
]
