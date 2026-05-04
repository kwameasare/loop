"""Pass12 Telegram Studio connect tests."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from loop_channels_telegram import (
    TelegramBotProfile,
    TelegramConnectFlow,
    TelegramConnectRequest,
)


def test_telegram_connect_flow_sets_webhook() -> None:
    provisioner = _FakeTelegramProvisioner()
    result = TelegramConnectFlow(provisioner).connect(
        TelegramConnectRequest(
            workspace_id="ws",
            bot_token_secret_ref="telegram-token",
            webhook_base_url="https://loop.example",
        )
    )
    assert result.ready
    assert result.bot_username == "loop_bot"
    assert provisioner.webhook == ("telegram-token", "https://loop.example/channels/telegram/webhook")


def test_telegram_connect_requires_https() -> None:
    with pytest.raises(ValueError):
        TelegramConnectFlow(_FakeTelegramProvisioner()).connect(
            TelegramConnectRequest(
                workspace_id="ws",
                bot_token_secret_ref="telegram-token",
                webhook_base_url="http://loop.local",
            )
        )


@dataclass(slots=True)
class _FakeTelegramProvisioner:
    webhook: tuple[str, str] | None = None

    def get_me(self, bot_token_secret_ref: str) -> TelegramBotProfile:
        assert bot_token_secret_ref == "telegram-token"
        return TelegramBotProfile(bot_id="bot-1", username="loop_bot", can_join_groups=True)

    def set_webhook(self, *, bot_token_secret_ref: str, webhook_url: str) -> None:
        self.webhook = (bot_token_secret_ref, webhook_url)
