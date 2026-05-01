"""Provider catalog for gateway routing.

The gateway keeps provider facts in strict data models so routing decisions
can be tested without network cassettes: model prefixes, endpoint style,
relative cost, relative latency, and quality tier all live here.
"""

from __future__ import annotations

from enum import StrEnum
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ProviderFamily(StrEnum):
    BEDROCK = "bedrock"
    VERTEX = "vertex"
    MISTRAL = "mistral"
    COHERE = "cohere"
    GROQ = "groq"
    VLLM = "vllm"
    OPENAI_COMPATIBLE = "openai_compatible"


class AuthHeaderStyle(StrEnum):
    AWS_SIGV4 = "aws_sigv4"
    GOOGLE_ADC = "google_adc"
    BEARER = "bearer"
    X_API_KEY = "x-api-key"
    NONE = "none"


class ProviderProfile(_StrictModel):
    """Static provider capabilities consumed by routers and adapters."""

    name: str
    display_name: str
    family: ProviderFamily
    model_prefixes: tuple[str, ...] = Field(min_length=1)
    base_url: str
    endpoint_path: str = "/v1/chat/completions"
    auth_header_style: AuthHeaderStyle = AuthHeaderStyle.BEARER
    quality_tier: int = Field(ge=1, le=5)
    latency_tier: int = Field(ge=1, le=5)
    cost_tier: int = Field(ge=1, le=5)
    supports_streaming: bool = True
    supports_embeddings: bool = False
    default_timeout_ms: int = Field(default=30_000, ge=100)
    tags: tuple[str, ...] = ()

    def supports_model(self, model: str) -> bool:
        return any(model.startswith(prefix) for prefix in self.model_prefixes)


class ProviderCatalog:
    """Immutable lookup over known provider profiles."""

    def __init__(self, profiles: tuple[ProviderProfile, ...] | None = None) -> None:
        selected = profiles or default_provider_profiles()
        by_name: dict[str, ProviderProfile] = {}
        for profile in selected:
            if profile.name in by_name:
                raise ValueError(f"duplicate provider profile: {profile.name}")
            by_name[profile.name] = profile
        self._profiles = MappingProxyType(by_name)

    @property
    def all(self) -> tuple[ProviderProfile, ...]:
        return tuple(self._profiles.values())

    def profile(self, name: str) -> ProviderProfile:
        try:
            return self._profiles[name]
        except KeyError as exc:
            raise KeyError(f"unknown provider profile: {name}") from exc

    def eligible(
        self,
        model: str,
        *,
        require_embedding: bool = False,
    ) -> tuple[ProviderProfile, ...]:
        profiles: list[ProviderProfile] = []
        for profile in self._profiles.values():
            if not profile.supports_model(model):
                continue
            if require_embedding and not profile.supports_embeddings:
                continue
            if not require_embedding and not profile.supports_streaming:
                continue
            profiles.append(profile)
        return tuple(profiles)


def default_provider_profiles() -> tuple[ProviderProfile, ...]:
    """Return the production provider catalog used by routing tests."""

    return (
        ProviderProfile(
            name="bedrock",
            display_name="AWS Bedrock",
            family=ProviderFamily.BEDROCK,
            model_prefixes=("anthropic.", "mistral.", "meta."),
            base_url="https://bedrock-runtime.aws",
            endpoint_path="/model/{model}/invoke-with-response-stream",
            auth_header_style=AuthHeaderStyle.AWS_SIGV4,
            quality_tier=5,
            latency_tier=3,
            cost_tier=3,
            tags=("anthropic", "mistral", "llama"),
        ),
        ProviderProfile(
            name="vertex",
            display_name="Google Vertex AI",
            family=ProviderFamily.VERTEX,
            model_prefixes=("gemini-",),
            base_url="https://aiplatform.googleapis.com",
            endpoint_path="/v1/projects/{project}/locations/{region}/publishers/google/models/{model}",
            auth_header_style=AuthHeaderStyle.GOOGLE_ADC,
            quality_tier=5,
            latency_tier=3,
            cost_tier=3,
            tags=("gemini", "google"),
        ),
        ProviderProfile(
            name="mistral",
            display_name="Mistral AI",
            family=ProviderFamily.MISTRAL,
            model_prefixes=("mistral-", "codestral-"),
            base_url="https://api.mistral.ai",
            quality_tier=4,
            latency_tier=2,
            cost_tier=2,
            tags=("coding", "reasoning"),
        ),
        ProviderProfile(
            name="cohere",
            display_name="Cohere",
            family=ProviderFamily.COHERE,
            model_prefixes=("command-r", "embed-"),
            base_url="https://api.cohere.com",
            endpoint_path="/v2/chat",
            auth_header_style=AuthHeaderStyle.BEARER,
            quality_tier=4,
            latency_tier=3,
            cost_tier=3,
            supports_embeddings=True,
            tags=("rag", "embed"),
        ),
        ProviderProfile(
            name="groq",
            display_name="Groq",
            family=ProviderFamily.GROQ,
            model_prefixes=("llama-3.3", "qwen-"),
            base_url="https://api.groq.com/openai",
            quality_tier=3,
            latency_tier=1,
            cost_tier=1,
            default_timeout_ms=10_000,
            tags=("lpu", "low-latency"),
        ),
        ProviderProfile(
            name="vllm",
            display_name="Self-hosted vLLM",
            family=ProviderFamily.VLLM,
            model_prefixes=("vllm-",),
            base_url="http://localhost:8000",
            auth_header_style=AuthHeaderStyle.NONE,
            quality_tier=3,
            latency_tier=2,
            cost_tier=1,
            tags=("self-hosted", "openai-compatible"),
        ),
        ProviderProfile(
            name="together",
            display_name="Together AI",
            family=ProviderFamily.OPENAI_COMPATIBLE,
            model_prefixes=("together-",),
            base_url="https://api.together.xyz",
            quality_tier=4,
            latency_tier=2,
            cost_tier=2,
            tags=("openai-compatible",),
        ),
        ProviderProfile(
            name="replicate",
            display_name="Replicate",
            family=ProviderFamily.OPENAI_COMPATIBLE,
            model_prefixes=("replicate-",),
            base_url="https://api.replicate.com",
            endpoint_path="/v1/predictions",
            quality_tier=3,
            latency_tier=4,
            cost_tier=3,
            tags=("openai-compatible",),
        ),
        ProviderProfile(
            name="fireworks",
            display_name="Fireworks AI",
            family=ProviderFamily.OPENAI_COMPATIBLE,
            model_prefixes=("fireworks-",),
            base_url="https://api.fireworks.ai/inference",
            quality_tier=4,
            latency_tier=2,
            cost_tier=1,
            tags=("openai-compatible",),
        ),
    )


__all__ = [
    "AuthHeaderStyle",
    "ProviderCatalog",
    "ProviderFamily",
    "ProviderProfile",
    "default_provider_profiles",
]
