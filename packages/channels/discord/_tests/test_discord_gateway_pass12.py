# ruff: noqa: S105,S106
"""Pass12 Discord gateway and connect tests."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from loop_channels_discord import (
    DiscordBotProfile,
    DiscordConnectFlow,
    DiscordConnectRequest,
    DiscordGatewayMessageParser,
)

WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000001")
AGENT_ID = UUID("00000000-0000-0000-0000-000000000002")
CONVERSATION_ID = UUID("00000000-0000-0000-0000-000000000003")


def test_discord_gateway_message_create_requires_bot_mention() -> None:
    parser = DiscordGatewayMessageParser()
    event = parser.parse_message_create(
        {
            "content": "<@bot-1> run the report",
            "author": {"id": "user-1"},
            "channel_id": "channel-1",
        },
        workspace_id=WORKSPACE_ID,
        agent_id=AGENT_ID,
        conversation_id=CONVERSATION_ID,
        bot_user_id="bot-1",
    )
    assert event is not None
    assert event.text == "run the report"
    assert event.metadata["channel_id"] == "channel-1"

    ignored = parser.parse_message_create(
        {"content": "hello", "author": {"id": "user-1"}, "channel_id": "channel-1"},
        workspace_id=WORKSPACE_ID,
        agent_id=AGENT_ID,
        conversation_id=CONVERSATION_ID,
        bot_user_id="bot-1",
    )
    assert ignored is None


def test_discord_connect_flow_registers_slash_command() -> None:
    provisioner = _FakeDiscordProvisioner()
    result = DiscordConnectFlow(provisioner).connect(
        DiscordConnectRequest(
            workspace_id="ws",
            bot_token_secret_ref="discord-token",
            public_key="pub",
            guild_id="guild-1",
        )
    )
    assert result.ready
    assert result.slash_command_registered
    assert provisioner.registered == ("app-1", "guild-1", "loop", "Ask the Loop agent")


@dataclass(slots=True)
class _FakeDiscordProvisioner:
    registered: tuple[str, str | None, str, str] | None = None

    def get_bot_profile(self, bot_token_secret_ref: str) -> DiscordBotProfile:
        assert bot_token_secret_ref == "discord-token"
        return DiscordBotProfile(application_id="app-1", bot_user_id="bot-1")

    def register_slash_command(
        self,
        *,
        application_id: str,
        guild_id: str | None,
        name: str,
        description: str,
    ) -> None:
        self.registered = (application_id, guild_id, name, description)
