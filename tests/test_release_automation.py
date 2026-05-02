"""Validate the 1.0 release-notes draft and release-please wiring (S670).

Asserts:

* CHANGELOG.md follows Keep-a-Changelog 1.1.0 conventions: header refers to
  Keep-a-Changelog and SemVer, has Unreleased + 1.0.0 sections, uses
  recognized section names, and ships compare/release link footer refs.
* release-please config files are valid JSON and consistent with each other
  (manifest version matches the latest CHANGELOG entry).
* The release-please workflow exists, runs on push-to-main, and uses the
  v4 Google action with the expected config/manifest paths.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
RP_CONFIG = REPO_ROOT / "release-please-config.json"
RP_MANIFEST = REPO_ROOT / ".release-please-manifest.json"
RP_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release-please.yml"

RECOGNIZED_SECTIONS = {
    "Added",
    "Changed",
    "Deprecated",
    "Removed",
    "Fixed",
    "Security",
    "Performance",
    "Documentation",
    "Dependencies",
}


def _changelog_text() -> str:
    return CHANGELOG.read_text(encoding="utf-8")


def test_changelog_has_keep_a_changelog_header() -> None:
    body = _changelog_text()
    assert "Keep a Changelog" in body
    assert "Semantic Versioning" in body


def test_changelog_has_unreleased_and_v1() -> None:
    body = _changelog_text()
    assert re.search(r"^## \[Unreleased\]", body, re.MULTILINE)
    assert re.search(r"^## \[1\.0\.0\]", body, re.MULTILINE)


def test_changelog_uses_recognized_section_names() -> None:
    body = _changelog_text()
    used = set(re.findall(r"^### ([A-Z][A-Za-z]+)$", body, re.MULTILINE))
    unknown = used - RECOGNIZED_SECTIONS
    assert unknown == set(), f"non-Keep-a-Changelog sections: {unknown}"


def test_changelog_link_refs_present() -> None:
    body = _changelog_text()
    # Footer link references for each version section.
    assert "[Unreleased]:" in body
    assert "[1.0.0]:" in body


def test_release_please_config_valid_json() -> None:
    cfg = json.loads(RP_CONFIG.read_text(encoding="utf-8"))
    assert cfg["release-type"] == "simple"
    assert cfg["include-v-in-tag"] is True
    assert "." in cfg["packages"]
    assert cfg["packages"]["."]["changelog-path"] == "CHANGELOG.md"


def test_release_please_manifest_valid_json() -> None:
    manifest = json.loads(RP_MANIFEST.read_text(encoding="utf-8"))
    assert "." in manifest
    # Manifest version must match the latest top-level entry in CHANGELOG.
    body = _changelog_text()
    first = re.search(r"^## \[(\d+\.\d+\.\d+)\]", body, re.MULTILINE)
    assert first is not None
    assert manifest["."] == first.group(1)


def test_release_please_workflow_wired() -> None:
    workflow = yaml.safe_load(RP_WORKFLOW.read_text(encoding="utf-8"))
    # YAML's "on" key parses as the Python boolean True.
    triggers = workflow.get("on") or workflow.get(True)
    assert triggers is not None
    assert "main" in triggers["push"]["branches"]
    perms = workflow["permissions"]
    assert perms["contents"] == "write"
    assert perms["pull-requests"] == "write"
    steps = workflow["jobs"]["release-please"]["steps"]
    uses = [s.get("uses", "") for s in steps]
    assert any("googleapis/release-please-action@v4" in u for u in uses)
    rp_step = next(
        s for s in steps if "googleapis/release-please-action" in s.get("uses", "")
    )
    assert rp_step["with"]["config-file"] == "release-please-config.json"
    assert rp_step["with"]["manifest-file"] == ".release-please-manifest.json"
