"""Unit checks for tools/license_check.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import license_check  # type: ignore[import-not-found]


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_license_check_flags_banned_license(tmp_path: Path) -> None:
    sbom = tmp_path / "sbom.json"
    allow = tmp_path / "allow.json"

    _write_json(
        sbom,
        {
            "components": [
                {
                    "name": "badpkg",
                    "type": "library",
                    "purl": "pkg:pypi/badpkg@1.0.0",
                    "licenses": [{"license": {"id": "GPL-3.0-only"}}],
                }
            ]
        },
    )
    _write_json(allow, {"allow": []})

    errors = license_check.check_licenses(sbom, allow)
    assert any("banned license detected" in err for err in errors)


def test_license_check_allows_nonexpired_allowlist_exception(tmp_path: Path) -> None:
    sbom = tmp_path / "sbom.json"
    allow = tmp_path / "allow.json"

    _write_json(
        sbom,
        {
            "components": [
                {
                    "name": "dualpkg",
                    "type": "library",
                    "purl": "pkg:pypi/dualpkg@2.0.0",
                    "licenses": [{"license": {"id": "LGPL-3.0-only"}}],
                }
            ]
        },
    )
    _write_json(
        allow,
        {
            "allow": [
                {
                    "package": "dualpkg",
                    "license": "LGPL-3.0-only",
                    "expires": "2099-01-01",
                    "reason": "dual-licensed with commercial exception",
                }
            ]
        },
    )

    assert license_check.check_licenses(sbom, allow) == []


def test_license_check_rejects_expired_allowlist_entry(tmp_path: Path) -> None:
    sbom = tmp_path / "sbom.json"
    allow = tmp_path / "allow.json"

    _write_json(sbom, {"components": []})
    _write_json(
        allow,
        {
            "allow": [
                {
                    "package": "*",
                    "license": "GPL-3.0-only",
                    "expires": "2000-01-01",
                    "reason": "expired",
                }
            ]
        },
    )

    errors = license_check.check_licenses(sbom, allow)
    assert any("expired allowlist entry" in err for err in errors)
