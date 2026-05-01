"""Discord gateway and Studio connect helpers."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from loop_channels_core import InboundEvent, InboundEventKind
from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DiscordBotProfile(_StrictModel):
    application_id: str
    bot_user_id: str
    guild_ids: tuple[str, ...] = ()


class DiscordConnectRequest(_StrictModel):
    workspace_id: str
    bot_token_secret_ref: str
    public_key: str
    guild_id: str | None = None


class DiscordConnectResult(_StrictModel):
    workspace_id: str
    application_id: str
    bot_user_id: str
    slash_command_registered: bool
    ready: bool


class DiscordProvisioner(Protocol):
    def get_bot_profile(self, bot_token_secret_ref: str) -> DiscordBotProfile: ...

    def register_slash_command(
        self,
        *,
        application_id: str,
        guild_id: str | None,
        name: str,
        description: str,
    ) -> None: ...


class DiscordConnectFlow:
    def __init__(self, provisioner: DiscordProvisioner) -> None:
        self._provisioner = provisioner

    def connect(self, request: DiscordConnectRequest) -> DiscordConnectResult:
        profile = self._provisioner.get_bot_profile(request.bot_token_secret_ref)
        self._provisioner.register_slash_command(
            application_id=profile.application_id,
            guild_id=request.guild_id,
            name="loop",
            description="Ask the Loop agent",
        )
        return DiscordConnectResult(
            workspace_id=request.workspace_id,
            application_id=profile.application_id,
            bot_user_id=profile.bot_user_id,
            slash_command_registered=True,
            ready=True,
        )


class DiscordGatewayMessageParser:
    def parse_message_create(
        self,
        payload: dict[str, object],
        *,
        workspace_id: UUID,
        agent_id: UUID,
        conversation_id: UUID,
        bot_user_id: str,
    ) -> InboundEvent | None:
        content = payload.get("content")
        author = payload.get("author")
        if not isinstance(content, str) or not isinstance(author, dict):
            return None
        mention = f"<@{bot_user_id}>"
        if mention not in content:
            return None
        user_id = author.get("id")
        if not isinstance(user_id, str) or user_id == bot_user_id:
            return None
        text = content.replace(mention, "").strip()
        if not text:
            return None
        return InboundEvent(
            workspace_id=workspace_id,
            agent_id=agent_id,
            conversation_id=conversation_id,
            kind=InboundEventKind.MESSAGE,
            user_id=user_id,
            text=text,
            metadata={"channel_id": str(payload.get("channel_id", ""))},
        )


__all__ = [
    "DiscordBotProfile",
    "DiscordConnectFlow",
    "DiscordConnectRequest",
    "DiscordConnectResult",
    "DiscordGatewayMessageParser",
    "DiscordProvisioner",
]
