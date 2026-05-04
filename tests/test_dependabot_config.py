"""Checks for Dependabot multi-ecosystem coverage and major-version policy."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEPENDABOT = ROOT / ".github" / "dependabot.yml"
POLICY = ROOT / "loop_implementation" / "engineering" / "DEPENDENCY_POLICY.md"


def _updates() -> list[dict[str, Any]]:
    data = cast(dict[str, Any], yaml.safe_load(DEPENDABOT.read_text()))
    return cast(list[dict[str, Any]], data["updates"])


def test_dependabot_covers_all_required_ecosystems() -> None:
    ecosystems = {entry["package-ecosystem"] for entry in _updates()}

    assert {"pip", "npm", "gomod", "docker", "github-actions"} <= ecosystems


def test_dependabot_uses_weekly_minor_patch_groups_and_ignores_major() -> None:
    for entry in _updates():
        schedule = cast(dict[str, Any], entry["schedule"])
        assert schedule["interval"] == "weekly"

        groups = cast(dict[str, Any], entry["groups"])
        assert groups, "each update entry must define a group for minor/patch updates"
        group_payload = next(iter(groups.values()))
        assert group_payload["update-types"] == ["minor", "patch"]

        ignore = cast(list[dict[str, Any]], entry["ignore"])
        assert any(
            item.get("dependency-name") == "*"
            and item.get("update-types") == ["version-update:semver-major"]
            for item in ignore
        )


def test_dependency_policy_doc_links_dependabot_and_manual_major_flow() -> None:
    text = POLICY.read_text()

    assert ".github/dependabot.yml" in text
    assert "Major updates are ignored by Dependabot" in text
    assert "manually owned upgrade PRs" in text
