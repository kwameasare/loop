"""Studio OAuth connect flow for Slack."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class SlackInstallResult(_StrictModel):
    team_id: str
    team_name: str
    bot_user_id: str
    bot_token_secret_ref: str


class SlackConnectRequest(_StrictModel):
    workspace_id: str
    code: str
    redirect_uri: str


class SlackConnectResult(_StrictModel):
    workspace_id: str
    team_id: str
    team_name: str
    bot_user_id: str
    ready: bool


class SlackOAuthClient(Protocol):
    def exchange_code(self, *, code: str, redirect_uri: str) -> SlackInstallResult: ...


class SlackConnectFlow:
    def __init__(self, oauth: SlackOAuthClient) -> None:
        self._oauth = oauth

    def connect(self, request: SlackConnectRequest) -> SlackConnectResult:
        if not request.redirect_uri.startswith("https://"):
            raise ValueError("redirect_uri must be https")
        install = self._oauth.exchange_code(code=request.code, redirect_uri=request.redirect_uri)
        return SlackConnectResult(
            workspace_id=request.workspace_id,
            team_id=install.team_id,
            team_name=install.team_name,
            bot_user_id=install.bot_user_id,
            ready=True,
        )


__all__ = [
    "SlackConnectFlow",
    "SlackConnectRequest",
    "SlackConnectResult",
    "SlackInstallResult",
    "SlackOAuthClient",
]
