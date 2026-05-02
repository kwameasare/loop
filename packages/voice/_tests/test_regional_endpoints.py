"""S653 coverage for regional ASR/TTS endpoint selection."""

from __future__ import annotations

from typing import cast

import pytest
from loop_voice.asr_deepgram import DeepgramConfig, deepgram_url
from loop_voice.regional_endpoints import (
    ProviderName,
    RegionalEndpointError,
    nearest_voice_region,
    provider_base_url,
    resolve_voice_endpoint,
)
from loop_voice.tts_cartesia import CartesiaConfig, cartesia_url
from loop_voice.tts_elevenlabs import ElevenLabsConfig, elevenlabs_url


def test_nearest_voice_region_selects_eu_west_and_ap_south() -> None:
    assert nearest_voice_region("eu-central") == "eu-west"
    assert nearest_voice_region("ap_southeast") == "ap-south"


def test_resolved_endpoint_builds_adapter_urls() -> None:
    deepgram = resolve_voice_endpoint("deepgram", "eu-central")
    deepgram_cfg = DeepgramConfig(api_key="k")
    assert deepgram.region == "eu-west"
    assert deepgram.expected_rtt_ms == 22
    assert deepgram_url(deepgram_cfg, base=deepgram.base_url).startswith(
        "wss://voice.eu-west.loop.example/deepgram/v1/listen?"
    )

    elevenlabs = resolve_voice_endpoint("elevenlabs", "ap-southeast")
    elevenlabs_cfg = ElevenLabsConfig(api_key="k", voice_id="v")
    assert elevenlabs.region == "ap-south"
    assert "/elevenlabs/v1/text-to-speech/v/stream-input?" in elevenlabs_url(
        elevenlabs_cfg, base=elevenlabs.base_url
    )

    cartesia = resolve_voice_endpoint("cartesia", "ap-south")
    cartesia_cfg = CartesiaConfig(api_key="k", voice_id="v")
    assert cartesia.region == "ap-south"
    assert cartesia_url(cartesia_cfg, base=cartesia.base_url).startswith(
        "wss://voice.ap-south.loop.example/cartesia/tts/websocket?"
    )


def test_regional_endpoint_rejects_unknown_routes() -> None:
    with pytest.raises(RegionalEndpointError):
        nearest_voice_region("moon-base")

    with pytest.raises(RegionalEndpointError):
        provider_base_url(cast(ProviderName, "unknown"), "eu-west")
