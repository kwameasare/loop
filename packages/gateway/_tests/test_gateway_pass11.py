"""Pass11 gateway tests: provider catalog, routing, failover, and eval suite."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest
from loop_gateway.provider_eval import (
    ProviderRunSample,
    standard_gateway_eval_suite,
    summarize_provider_run,
)
from loop_gateway.provider_profiles import ProviderCatalog, ProviderFamily, ProviderProfile
from loop_gateway.provider_routing import (
    ProviderCapability,
    ProviderFailoverRunner,
    ProviderRateLimitConfig,
    ProviderRateLimiter,
    ProviderRateLimitExceeded,
    ProviderRouter,
    RouteIntent,
    RouteRequest,
    WorkspaceAliasResolver,
)
from loop_gateway.providers import EmbeddingRequest, OpenAICompatibleProvider
from loop_gateway.types import (
    GatewayDelta,
    GatewayDone,
    GatewayError,
    GatewayEvent,
    GatewayMessage,
    GatewayRequest,
)


def _request(model: str, request_id: str = "req-pass11") -> GatewayRequest:
    return GatewayRequest(
        request_id=request_id,
        workspace_id="ws-pass11",
        model=model,
        messages=(GatewayMessage(role="user", content="tell me a story"),),
    )


async def _wrap(lines: tuple[str, ...]) -> AsyncIterator[str]:
    for line in lines:
        yield line


def test_default_catalog_covers_target_providers() -> None:
    catalog = ProviderCatalog()
    names = {profile.name for profile in catalog.all}
    assert {
        "bedrock",
        "vertex",
        "mistral",
        "cohere",
        "groq",
        "vllm",
        "together",
        "replicate",
        "fireworks",
    } <= names
    assert catalog.eligible("anthropic.claude-3-5-sonnet-20240620-v1:0")[0].name == "bedrock"
    assert catalog.eligible("gemini-1.5-pro")[0].name == "vertex"
    assert catalog.eligible("mistral-large-latest")[0].name == "mistral"
    assert catalog.eligible("command-r-plus")[0].name == "cohere"
    assert catalog.eligible("llama-3.3-70b-versatile")[0].name == "groq"
    assert catalog.eligible("vllm-local-llama")[0].name == "vllm"
    assert catalog.eligible("embed-english-v3.0", require_embedding=True)[0].name == "cohere"


@pytest.mark.parametrize(
    ("provider_name", "model"),
    (
        ("bedrock", "anthropic.claude-3-5-sonnet-20240620-v1:0"),
        ("vertex", "gemini-1.5-flash"),
        ("mistral", "mistral-large-latest"),
        ("cohere", "command-r-plus"),
        ("groq", "llama-3.3-70b-versatile"),
        ("vllm", "vllm-local-llama"),
        ("together", "together-meta-llama"),
        ("replicate", "replicate-llama"),
        ("fireworks", "fireworks-qwen"),
    ),
)
@pytest.mark.asyncio
async def test_openai_compatible_provider_streams_each_profile(
    provider_name: str,
    model: str,
) -> None:
    lines = (
        'data: {"choices":[{"delta":{"content":"Hello"}}]}',
        'data: {"choices":[{"delta":{"content":" Loop"}}]}',
        'data: {"usage":{"prompt_tokens":100,"completion_tokens":25}}',
        "data: [DONE]",
    )
    profile = ProviderCatalog().profile(provider_name)
    provider = OpenAICompatibleProvider(profile, lambda _req: _wrap(lines))

    events = [event async for event in provider.stream(_request(model))]

    assert provider.supports(model)
    assert [event.text for event in events if isinstance(event, GatewayDelta)] == [
        "Hello",
        " Loop",
    ]
    done = events[-1]
    assert isinstance(done, GatewayDone)
    assert done.usage.input_tokens == 100
    assert done.usage.output_tokens == 25
    assert done.cost_disclosed_markup_pct == 5.0


@pytest.mark.asyncio
async def test_cohere_embedding_path_parses_vectors_and_cost() -> None:
    profile = ProviderCatalog().profile("cohere")
    provider = OpenAICompatibleProvider(
        profile,
        lambda _req: _wrap(()),
        embedding_transport=lambda _req: _wrap(
            (
                (
                    '{"data":[{"embedding":[0.1,0.2]},{"embedding":[0.3,0.4]}],'
                    '"usage":{"prompt_tokens":100000,"completion_tokens":0}}'
                ),
            )
        ),
    )

    result = await provider.embed(
        EmbeddingRequest(
            request_id="embed-1",
            workspace_id="ws-pass11",
            model="embed-english-v3.0",
            inputs=("hello", "world"),
        )
    )

    assert result.vectors == ((0.1, 0.2), (0.3, 0.4))
    assert result.usage.input_tokens == 100000
    assert result.cost_usd > 0


def test_workspace_alias_and_router_select_expected_provider() -> None:
    aliases = WorkspaceAliasResolver({"ws-pass11": {"loop:fast": "llama-3.3-70b-versatile"}})
    router = ProviderRouter(aliases=aliases)
    decision = router.route(
        RouteRequest(workspace_id="ws-pass11", model="loop:fast", intent=RouteIntent.FAST)
    )
    assert decision.primary.provider == "groq"
    assert decision.primary.model == "llama-3.3-70b-versatile"


def test_router_honors_intent_preferred_and_disabled() -> None:
    catalog = ProviderCatalog(
        (
            ProviderProfile(
                name="cheap-fast",
                display_name="Cheap Fast",
                family=ProviderFamily.OPENAI_COMPATIBLE,
                model_prefixes=("shared-",),
                base_url="https://fast.example",
                quality_tier=2,
                latency_tier=1,
                cost_tier=1,
            ),
            ProviderProfile(
                name="premium",
                display_name="Premium",
                family=ProviderFamily.OPENAI_COMPATIBLE,
                model_prefixes=("shared-",),
                base_url="https://premium.example",
                quality_tier=5,
                latency_tier=4,
                cost_tier=5,
            ),
        )
    )
    router = ProviderRouter(catalog)

    fast = router.route(
        RouteRequest(workspace_id="ws", model="shared-model", intent=RouteIntent.FAST)
    )
    assert fast.primary.provider == "cheap-fast"

    quality = router.route(
        RouteRequest(workspace_id="ws", model="shared-model", intent=RouteIntent.QUALITY)
    )
    assert quality.primary.provider == "premium"

    preferred = router.route(
        RouteRequest(
            workspace_id="ws",
            model="shared-model",
            intent=RouteIntent.FAST,
            preferred_provider="premium",
        )
    )
    assert preferred.primary.provider == "premium"

    disabled = router.route(
        RouteRequest(
            workspace_id="ws",
            model="shared-model",
            intent=RouteIntent.QUALITY,
            disabled_providers=("premium",),
        )
    )
    assert disabled.primary.provider == "cheap-fast"


def test_router_requires_embedding_capability() -> None:
    decision = ProviderRouter().route(
        RouteRequest(
            workspace_id="ws-pass11",
            model="embed-english-v3.0",
            capability=ProviderCapability.EMBEDDING,
        )
    )
    assert decision.primary.provider == "cohere"


@pytest.mark.asyncio
async def test_provider_failover_uses_next_route_and_records_trace() -> None:
    catalog = ProviderCatalog(
        (
            ProviderProfile(
                name="primary",
                display_name="Primary",
                family=ProviderFamily.OPENAI_COMPATIBLE,
                model_prefixes=("shared-",),
                base_url="https://primary.example",
                quality_tier=4,
                latency_tier=1,
                cost_tier=1,
            ),
            ProviderProfile(
                name="fallback",
                display_name="Fallback",
                family=ProviderFamily.OPENAI_COMPATIBLE,
                model_prefixes=("shared-",),
                base_url="https://fallback.example",
                quality_tier=3,
                latency_tier=2,
                cost_tier=2,
            ),
        )
    )
    providers = {
        "primary": _FakeProvider("primary", (GatewayError(code="GW-5XX", message="boom"),)),
        "fallback": _FakeProvider(
            "fallback",
            (
                GatewayDelta(text="ok"),
                GatewayDone(usage={"input_tokens": 1, "output_tokens": 1}, cost_usd=0.01),
            ),
        ),
    }
    runner = ProviderFailoverRunner(providers, ProviderRouter(catalog))

    events = [
        event
        async for event in runner.stream(
            _request("shared-model"),
            RouteRequest(workspace_id="ws-pass11", model="shared-model"),
        )
    ]

    assert isinstance(events[0], GatewayDelta)
    assert isinstance(events[-1], GatewayDone)
    assert runner.last_trace is not None
    assert [attempt.provider for attempt in runner.last_trace.attempts] == [
        "primary",
        "fallback",
    ]


def test_provider_rate_limiter_isolates_provider_workspace_and_key() -> None:
    now = [0.0]
    limiter = ProviderRateLimiter(
        ProviderRateLimitConfig(capacity=2, refill_per_second=1),
        clock=lambda: now[0],
    )
    limiter.acquire(provider="groq", workspace_id="ws", key_id="key-a")
    limiter.acquire(provider="groq", workspace_id="ws", key_id="key-a")
    with pytest.raises(ProviderRateLimitExceeded) as exc:
        limiter.acquire(provider="groq", workspace_id="ws", key_id="key-a")
    assert exc.value.code == "LOOP-GW-301"

    limiter.acquire(provider="groq", workspace_id="ws", key_id="key-b")
    limiter.acquire(provider="mistral", workspace_id="ws", key_id="key-a")
    now[0] = 1.0
    limiter.acquire(provider="groq", workspace_id="ws", key_id="key-a")
    assert limiter.tokens(provider="groq", workspace_id="ws", key_id="key-a") == pytest.approx(0.0)


def test_standard_provider_eval_suite_has_50_prompts_and_report_gates() -> None:
    suite = standard_gateway_eval_suite()
    assert len(suite) == 50
    assert len({prompt.prompt_id for prompt in suite}) == 50

    samples = tuple(
        ProviderRunSample(
            provider="groq",
            prompt_id=prompt.prompt_id,
            quality_score=0.8,
            latency_ms=150,
            cost_usd=0.001,
        )
        for prompt in suite
    )
    report = summarize_provider_run(provider="groq", samples=samples)
    assert report.prompts_total == 50
    assert report.prompts_ok == 50
    assert report.mean_quality == 0.8
    assert report.p95_latency_ms == 150
    assert report.passed


@dataclass(slots=True)
class _FakeProvider:
    name: str
    events: tuple[GatewayEvent, ...]

    def supports(self, model: str) -> bool:
        return model.startswith("shared-")

    async def stream(self, request: GatewayRequest) -> AsyncIterator[GatewayEvent]:
        for event in self.events:
            yield event
