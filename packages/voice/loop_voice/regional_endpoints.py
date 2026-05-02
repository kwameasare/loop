"""Regional voice provider endpoint selection."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

VoiceRegion = Literal["us-east", "us-west", "eu-west", "ap-south"]
ProviderName = Literal["deepgram", "elevenlabs", "cartesia"]
LatencyMap = Mapping[str, Mapping[VoiceRegion, int]]
ProviderEndpointMap = Mapping[ProviderName, Mapping[VoiceRegion, str]]

VOICE_REGIONS: tuple[VoiceRegion, ...] = ("us-east", "us-west", "eu-west", "ap-south")

VOICE_REGIONAL_LATENCY_MS: dict[str, dict[VoiceRegion, int]] = {
    "us-east": {"us-east": 12, "us-west": 58, "eu-west": 76, "ap-south": 214},
    "us-west": {"us-east": 58, "us-west": 14, "eu-west": 142, "ap-south": 188},
    "eu-west": {"us-east": 76, "us-west": 142, "eu-west": 14, "ap-south": 122},
    "eu-central": {"us-east": 82, "us-west": 150, "eu-west": 22, "ap-south": 128},
    "ap-south": {"us-east": 214, "us-west": 188, "eu-west": 122, "ap-south": 18},
    "ap-southeast": {"us-east": 194, "us-west": 132, "eu-west": 168, "ap-south": 74},
    "af-south": {"us-east": 138, "us-west": 196, "eu-west": 92, "ap-south": 142},
}

VOICE_PROVIDER_BASE_URLS: dict[ProviderName, dict[VoiceRegion, str]] = {
    "deepgram": {
        "us-east": "wss://voice.us-east.loop.example/deepgram",
        "us-west": "wss://voice.us-west.loop.example/deepgram",
        "eu-west": "wss://voice.eu-west.loop.example/deepgram",
        "ap-south": "wss://voice.ap-south.loop.example/deepgram",
    },
    "elevenlabs": {
        "us-east": "wss://voice.us-east.loop.example/elevenlabs",
        "us-west": "wss://voice.us-west.loop.example/elevenlabs",
        "eu-west": "wss://voice.eu-west.loop.example/elevenlabs",
        "ap-south": "wss://voice.ap-south.loop.example/elevenlabs",
    },
    "cartesia": {
        "us-east": "wss://voice.us-east.loop.example/cartesia",
        "us-west": "wss://voice.us-west.loop.example/cartesia",
        "eu-west": "wss://voice.eu-west.loop.example/cartesia",
        "ap-south": "wss://voice.ap-south.loop.example/cartesia",
    },
}


class RegionalEndpointError(ValueError):
    """Raised when a caller/provider cannot be routed regionally."""


@dataclass(frozen=True, slots=True)
class VoiceRegionalEndpoint:
    provider: ProviderName
    region: VoiceRegion
    base_url: str
    expected_rtt_ms: int


def _source_key(source_region: str) -> str:
    return source_region.strip().lower().replace("_", "-")


def nearest_voice_region(
    source_region: str,
    *,
    latency_map: LatencyMap = VOICE_REGIONAL_LATENCY_MS,
) -> VoiceRegion:
    """Select the lowest-rtt supported voice region for a caller/source."""
    source_key = _source_key(source_region)
    candidates = latency_map.get(source_key)
    if candidates is None:
        raise RegionalEndpointError(f"no latency map for source region {source_region!r}")
    missing = [region for region in VOICE_REGIONS if region not in candidates]
    if missing:
        raise RegionalEndpointError(f"latency map for {source_key!r} misses {', '.join(missing)}")
    return min(VOICE_REGIONS, key=lambda region: (candidates[region], region))


def provider_base_url(
    provider: ProviderName,
    region: VoiceRegion,
    *,
    endpoints: ProviderEndpointMap = VOICE_PROVIDER_BASE_URLS,
) -> str:
    try:
        return endpoints[provider][region]
    except KeyError as exc:
        raise RegionalEndpointError(f"no {provider} endpoint for voice region {region}") from exc


def resolve_voice_endpoint(
    provider: ProviderName,
    source_region: str,
    *,
    latency_map: LatencyMap = VOICE_REGIONAL_LATENCY_MS,
    endpoints: ProviderEndpointMap = VOICE_PROVIDER_BASE_URLS,
) -> VoiceRegionalEndpoint:
    region = nearest_voice_region(source_region, latency_map=latency_map)
    return VoiceRegionalEndpoint(
        provider=provider,
        region=region,
        base_url=provider_base_url(provider, region, endpoints=endpoints),
        expected_rtt_ms=latency_map[_source_key(source_region)][region],
    )


__all__ = [
    "VOICE_PROVIDER_BASE_URLS",
    "VOICE_REGIONAL_LATENCY_MS",
    "VOICE_REGIONS",
    "LatencyMap",
    "ProviderEndpointMap",
    "ProviderName",
    "RegionalEndpointError",
    "VoiceRegion",
    "VoiceRegionalEndpoint",
    "nearest_voice_region",
    "provider_base_url",
    "resolve_voice_endpoint",
]
