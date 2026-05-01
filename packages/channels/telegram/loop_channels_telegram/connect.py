"""Studio connect flow for Telegram Bot API."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class TelegramBotProfile(_StrictModel):
    bot_id: str
    username: str
    can_join_groups: bool


class TelegramConnectRequest(_StrictModel):
    workspace_id: str
    bot_token_secret_ref: str
    webhook_base_url: str


class TelegramConnectResult(_StrictModel):
    workspace_id: str
    bot_username: str
    webhook_url: str
    ready: bool


class TelegramProvisioner(Protocol):
    def get_me(self, bot_token_secret_ref: str) -> TelegramBotProfile: ...

    def set_webhook(self, *, bot_token_secret_ref: str, webhook_url: str) -> None: ...


class TelegramConnectFlow:
    def __init__(self, provisioner: TelegramProvisioner) -> None:
        self._provisioner = provisioner

    def connect(self, request: TelegramConnectRequest) -> TelegramConnectResult:
        if not request.webhook_base_url.startswith("https://"):
            raise ValueError("webhook_base_url must be https")
        profile = self._provisioner.get_me(request.bot_token_secret_ref)
        webhook_url = f"{request.webhook_base_url.rstrip('/')}/channels/telegram/webhook"
        self._provisioner.set_webhook(
            bot_token_secret_ref=request.bot_token_secret_ref,
            webhook_url=webhook_url,
        )
        return TelegramConnectResult(
            workspace_id=request.workspace_id,
            bot_username=profile.username,
            webhook_url=webhook_url,
            ready=True,
        )


__all__ = [
    "TelegramBotProfile",
    "TelegramConnectFlow",
    "TelegramConnectRequest",
    "TelegramConnectResult",
    "TelegramProvisioner",
]
