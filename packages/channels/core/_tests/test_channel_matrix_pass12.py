"""Pass12 cross-channel feature matrix tests."""

from __future__ import annotations

import pytest
from loop_channels_core import (
    AgentChannelMatrix,
    ChannelCapability,
    default_channel_profiles,
)


def test_default_channel_profiles_cover_mvp_surfaces() -> None:
    profiles = default_channel_profiles()
    channels = {profile.channel for profile in profiles}
    assert {"sms", "rcs", "discord", "teams", "telegram", "whatsapp"} <= channels


def test_agent_channel_matrix_blocks_unsupported_capability() -> None:
    matrix = AgentChannelMatrix(agent_id="agent-1", profiles=default_channel_profiles())
    matrix.require(channel="rcs", capability=ChannelCapability.RICH_CARD)
    matrix.require(channel="discord", capability=ChannelCapability.ATTACHMENTS)

    with pytest.raises(ValueError):
        matrix.require(channel="sms", capability=ChannelCapability.RICH_CARD)


def test_agent_channel_matrix_unknown_channel_is_key_error() -> None:
    matrix = AgentChannelMatrix(agent_id="agent-1", profiles=default_channel_profiles())
    with pytest.raises(KeyError):
        matrix.profile("fax")
