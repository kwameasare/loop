"""Cross-channel capability matrix."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ChannelCapability(StrEnum):
    TEXT = "text"
    RICH_CARD = "rich_card"
    SUGGESTED_REPLIES = "suggested_replies"
    ATTACHMENTS = "attachments"
    DELIVERY_RECEIPTS = "delivery_receipts"
    READ_RECEIPTS = "read_receipts"
    HUMAN_TAKEOVER = "human_takeover"
    TYPING = "typing"


class ChannelFeatureProfile(_StrictModel):
    channel: str
    capabilities: tuple[ChannelCapability, ...] = Field(min_length=1)
    max_text_chars: int = Field(ge=1)
    supports_threads: bool = False

    def supports(self, capability: ChannelCapability) -> bool:
        return capability in self.capabilities


class AgentChannelMatrix(_StrictModel):
    agent_id: str
    profiles: tuple[ChannelFeatureProfile, ...] = Field(min_length=1)

    def profile(self, channel: str) -> ChannelFeatureProfile:
        for profile in self.profiles:
            if profile.channel == channel:
                return profile
        raise KeyError(f"channel not configured: {channel}")

    def require(self, *, channel: str, capability: ChannelCapability) -> None:
        profile = self.profile(channel)
        if not profile.supports(capability):
            raise ValueError(f"{channel} does not support {capability.value}")


def default_channel_profiles() -> tuple[ChannelFeatureProfile, ...]:
    return (
        ChannelFeatureProfile(
            channel="sms",
            capabilities=(ChannelCapability.TEXT, ChannelCapability.HUMAN_TAKEOVER),
            max_text_chars=1_600,
        ),
        ChannelFeatureProfile(
            channel="rcs",
            capabilities=(
                ChannelCapability.TEXT,
                ChannelCapability.RICH_CARD,
                ChannelCapability.SUGGESTED_REPLIES,
                ChannelCapability.DELIVERY_RECEIPTS,
                ChannelCapability.READ_RECEIPTS,
                ChannelCapability.HUMAN_TAKEOVER,
            ),
            max_text_chars=3_072,
        ),
        ChannelFeatureProfile(
            channel="discord",
            capabilities=(
                ChannelCapability.TEXT,
                ChannelCapability.ATTACHMENTS,
                ChannelCapability.HUMAN_TAKEOVER,
            ),
            max_text_chars=2_000,
            supports_threads=True,
        ),
        ChannelFeatureProfile(
            channel="teams",
            capabilities=(
                ChannelCapability.TEXT,
                ChannelCapability.RICH_CARD,
                ChannelCapability.ATTACHMENTS,
                ChannelCapability.HUMAN_TAKEOVER,
            ),
            max_text_chars=28_000,
            supports_threads=True,
        ),
        ChannelFeatureProfile(
            channel="telegram",
            capabilities=(
                ChannelCapability.TEXT,
                ChannelCapability.ATTACHMENTS,
                ChannelCapability.HUMAN_TAKEOVER,
            ),
            max_text_chars=4_096,
        ),
        ChannelFeatureProfile(
            channel="whatsapp",
            capabilities=(
                ChannelCapability.TEXT,
                ChannelCapability.ATTACHMENTS,
                ChannelCapability.SUGGESTED_REPLIES,
                ChannelCapability.HUMAN_TAKEOVER,
            ),
            max_text_chars=4_096,
        ),
    )


__all__ = [
    "AgentChannelMatrix",
    "ChannelCapability",
    "ChannelFeatureProfile",
    "default_channel_profiles",
]
