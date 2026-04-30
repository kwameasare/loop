"""Slack app manifest builder (S227).

Slack's app-manifest API takes a YAML document that fully describes
permissions, events, and slash commands. We build that document
*from code* so:

1. The required scopes stay in lock-step with what
   :mod:`loop_channels_slack.channel` actually needs at runtime.
2. We never check a stale manifest into source.
3. Per-environment install flows can override callback URLs without
   forking the file.

The OAuth install flow itself (the ``/slack/install`` redirect plus
``/slack/oauth_redirect`` handler) lives in cp-api; this module is
the manifest contract the install flow renders.
"""

from __future__ import annotations

import yaml
from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "REQUIRED_BOT_SCOPES",
    "REQUIRED_EVENT_SUBSCRIPTIONS",
    "SlackManifestConfig",
    "build_manifest",
    "build_manifest_yaml",
]


# Scopes the Slack channel needs end-to-end. Order is alphabetical
# so manifest YAML diffs stay stable.
REQUIRED_BOT_SCOPES: tuple[str, ...] = (
    "app_mentions:read",
    "channels:history",
    "chat:write",
    "chat:write.public",
    "commands",
    "files:read",
    "groups:history",
    "im:history",
    "im:read",
    "im:write",
    "mpim:history",
    "reactions:read",
    "reactions:write",
    "team:read",
    "users:read",
    "users:read.email",
)


# Bot events the channel actually handles. Sorted, deduplicated.
REQUIRED_EVENT_SUBSCRIPTIONS: tuple[str, ...] = (
    "app_mention",
    "message.channels",
    "message.groups",
    "message.im",
    "message.mpim",
    "reaction_added",
)


class SlackManifestConfig(BaseModel):
    """Per-environment knobs for the manifest."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    app_name: str = Field(min_length=1, max_length=35)
    description: str = Field(min_length=1, max_length=140)
    base_url: str = Field(min_length=1)
    bot_user_display_name: str = Field(min_length=1, max_length=80)
    slash_command: str = Field(default="/loop", min_length=2, max_length=32)


def build_manifest(config: SlackManifestConfig) -> dict[str, object]:
    """Return the Slack manifest as a JSON-shaped ``dict``.

    Keys are output sorted by ``yaml.safe_dump(..., sort_keys=True)``
    so the rendered YAML is byte-stable across runs.
    """
    base = config.base_url.rstrip("/")
    return {
        "_metadata": {
            "major_version": 1,
            "minor_version": 1,
        },
        "display_information": {
            "name": config.app_name,
            "description": config.description,
            "background_color": "#0B1220",
        },
        "features": {
            "app_home": {
                "home_tab_enabled": True,
                "messages_tab_enabled": True,
                "messages_tab_read_only_enabled": False,
            },
            "bot_user": {
                "display_name": config.bot_user_display_name,
                "always_online": True,
            },
            "slash_commands": [
                {
                    "command": config.slash_command,
                    "url": f"{base}/v1/slack/commands",
                    "description": f"{config.app_name} commands",
                    "usage_hint": "help",
                    "should_escape": False,
                }
            ],
        },
        "oauth_config": {
            "redirect_urls": [f"{base}/v1/slack/oauth_redirect"],
            "scopes": {"bot": list(REQUIRED_BOT_SCOPES)},
        },
        "settings": {
            "event_subscriptions": {
                "request_url": f"{base}/v1/slack/events",
                "bot_events": list(REQUIRED_EVENT_SUBSCRIPTIONS),
            },
            "interactivity": {
                "is_enabled": True,
                "request_url": f"{base}/v1/slack/interactivity",
            },
            "org_deploy_enabled": False,
            "socket_mode_enabled": False,
            "token_rotation_enabled": True,
        },
    }


def build_manifest_yaml(config: SlackManifestConfig) -> str:
    """Render the manifest dict as deterministic YAML."""
    manifest = build_manifest(config)
    return yaml.safe_dump(manifest, sort_keys=True, default_flow_style=False)
