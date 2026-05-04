"""Pass12 Slack connect-flow tests."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from loop_channels_slack import (
    SlackConnectFlow,
    SlackConnectRequest,
    SlackInstallResult,
)


def test_slack_connect_flow_exchanges_oauth_code() -> None:
    oauth = _FakeSlackOAuth()
    result = SlackConnectFlow(oauth).connect(
        SlackConnectRequest(
            workspace_id="ws",
            code="oauth-code",
            redirect_uri="https://loop.example/slack/callback",
        )
    )
    assert result.ready
    assert result.team_id == "T1"
    assert oauth.seen == ("oauth-code", "https://loop.example/slack/callback")


def test_slack_connect_requires_https_redirect() -> None:
    with pytest.raises(ValueError):
        SlackConnectFlow(_FakeSlackOAuth()).connect(
            SlackConnectRequest(
                workspace_id="ws",
                code="oauth-code",
                redirect_uri="http://loop.local/callback",
            )
        )


@dataclass(slots=True)
class _FakeSlackOAuth:
    seen: tuple[str, str] | None = None

    def exchange_code(self, *, code: str, redirect_uri: str) -> SlackInstallResult:
        self.seen = (code, redirect_uri)
        return SlackInstallResult(
            team_id="T1",
            team_name="Loop Team",
            bot_user_id="Ubot",
            bot_token_secret_ref="slack-token",
        )
