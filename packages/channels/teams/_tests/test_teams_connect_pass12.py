# ruff: noqa: S106
"""Pass12 Teams connect and adaptive card tests."""

from __future__ import annotations

from dataclasses import dataclass

from loop_channels_teams import (
    TeamsAppManifest,
    TeamsConnectFlow,
    TeamsConnectRequest,
    render_adaptive_card,
)


def test_teams_connect_flow_uploads_manifest() -> None:
    provisioner = _FakeTeamsProvisioner()
    result = TeamsConnectFlow(provisioner).connect(
        TeamsConnectRequest(
            workspace_id="ws",
            tenant_id="tenant-1",
            bot_app_id="bot-app",
            bot_secret_ref="teams-secret",
            manifest_package="manifest.zip",
        )
    )
    assert result.ready
    assert result.uploaded
    assert result.app_id == "app-1"
    assert provisioner.seen is not None


def test_adaptive_card_renderer_outputs_submit_actions() -> None:
    attachment = render_adaptive_card(
        title="Approve handoff",
        body="Send this to an operator?",
        actions=("Approve", "Cancel"),
    )
    assert attachment["contentType"] == "application/vnd.microsoft.card.adaptive"
    content = attachment["content"]
    assert isinstance(content, dict)
    assert len(content["actions"]) == 2  # type: ignore[arg-type]


@dataclass(slots=True)
class _FakeTeamsProvisioner:
    seen: TeamsConnectRequest | None = None

    def upload_manifest(self, request: TeamsConnectRequest) -> TeamsAppManifest:
        self.seen = request
        return TeamsAppManifest(
            app_id="app-1",
            bot_id=request.bot_app_id,
            tenant_id=request.tenant_id,
            package_name=request.manifest_package,
        )
