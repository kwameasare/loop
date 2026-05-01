"""Teams Bot Framework connect and adaptive card helpers."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class TeamsAppManifest(_StrictModel):
    app_id: str
    bot_id: str
    tenant_id: str
    package_name: str


class TeamsConnectRequest(_StrictModel):
    workspace_id: str
    tenant_id: str
    bot_app_id: str
    bot_secret_ref: str
    manifest_package: str


class TeamsConnectResult(_StrictModel):
    workspace_id: str
    tenant_id: str
    app_id: str
    uploaded: bool
    ready: bool


class TeamsProvisioner(Protocol):
    def upload_manifest(self, request: TeamsConnectRequest) -> TeamsAppManifest: ...


class TeamsConnectFlow:
    def __init__(self, provisioner: TeamsProvisioner) -> None:
        self._provisioner = provisioner

    def connect(self, request: TeamsConnectRequest) -> TeamsConnectResult:
        manifest = self._provisioner.upload_manifest(request)
        return TeamsConnectResult(
            workspace_id=request.workspace_id,
            tenant_id=manifest.tenant_id,
            app_id=manifest.app_id,
            uploaded=True,
            ready=True,
        )


def render_adaptive_card(*, title: str, body: str, actions: tuple[str, ...] = ()) -> dict[str, object]:
    card: dict[str, object] = {
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": [
            {"type": "TextBlock", "text": title, "weight": "Bolder", "wrap": True},
            {"type": "TextBlock", "text": body, "wrap": True},
        ],
    }
    if actions:
        card["actions"] = [
            {"type": "Action.Submit", "title": action, "data": {"action": action}}
            for action in actions
        ]
    return {"contentType": "application/vnd.microsoft.card.adaptive", "content": card}


__all__ = [
    "TeamsAppManifest",
    "TeamsConnectFlow",
    "TeamsConnectRequest",
    "TeamsConnectResult",
    "TeamsProvisioner",
    "render_adaptive_card",
]
