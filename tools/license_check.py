#!/usr/bin/env python3
"""Fail CI when banned copyleft licenses appear in distributable Python components."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BANNED_PREFIXES = ("GPL-", "AGPL-", "LGPL-3")


@dataclass(frozen=True)
class AllowEntry:
    package: str
    license_id: str
    expires: dt.date
    reason: str


def _parse_date(raw: str) -> dt.date:
    return dt.date.fromisoformat(raw)


def _load_allowlist(path: Path) -> tuple[list[AllowEntry], list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    entries_raw = data.get("allow", [])
    if not isinstance(entries_raw, list):
        raise ValueError("allowlist field 'allow' must be a list")

    today = dt.date.today()
    entries: list[AllowEntry] = []
    errors: list[str] = []
    for entry in entries_raw:
        if not isinstance(entry, dict):
            errors.append(f"invalid allowlist entry: {entry!r}")
            continue
        package = str(entry.get("package", "")).strip().lower()
        license_id = str(entry.get("license", "")).strip().upper()
        expires_raw = str(entry.get("expires", "")).strip()
        reason = str(entry.get("reason", "")).strip()
        if not package or not license_id or not expires_raw:
            errors.append(f"allowlist entry missing required fields: {entry!r}")
            continue
        expires = _parse_date(expires_raw)
        if expires < today:
            errors.append(
                "expired allowlist entry: "
                f"package={package} license={license_id} expires={expires.isoformat()}"
            )
        entries.append(
            AllowEntry(
                package=package,
                license_id=license_id,
                expires=expires,
                reason=reason,
            )
        )
    return entries, errors


def _normalize_license(raw: Any) -> str | None:
    if isinstance(raw, dict):
        if "license" in raw:
            return _normalize_license(raw["license"])
        if "id" in raw and isinstance(raw["id"], str):
            return raw["id"].strip().upper()
        if "name" in raw and isinstance(raw["name"], str):
            return raw["name"].strip().upper()
        return None
    if isinstance(raw, str):
        value = raw.strip()
        return value.upper() if value else None
    return None


def _is_banned(license_id: str) -> bool:
    normalized = license_id.upper()
    return any(normalized.startswith(prefix) for prefix in BANNED_PREFIXES)


def _allowlisted(package: str, license_id: str, allowlist: list[AllowEntry]) -> bool:
    package_norm = package.lower()
    license_norm = license_id.upper()
    for entry in allowlist:
        if entry.package not in {"*", package_norm}:
            continue
        if entry.license_id != license_norm:
            continue
        return True
    return False


def _component_licenses(component: dict[str, Any]) -> list[str]:
    licenses = component.get("licenses")
    if not isinstance(licenses, list):
        return []
    normalized: list[str] = []
    for entry in licenses:
        parsed = _normalize_license(entry)
        if parsed:
            normalized.append(parsed)
    return normalized


def _is_distributable_python_component(component: dict[str, Any]) -> bool:
    purl = component.get("purl")
    if isinstance(purl, str) and purl.startswith("pkg:pypi/"):
        return True
    # Fall back to conservative filtering when purl is absent.
    comp_type = str(component.get("type", "")).lower()
    return comp_type in {"library", "application"}


def check_licenses(sbom_path: Path, allowlist_path: Path) -> list[str]:
    sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
    allowlist, errors = _load_allowlist(allowlist_path)

    components = sbom.get("components", [])
    if not isinstance(components, list):
        errors.append("sbom components must be a list")
        return errors

    for component_raw in components:
        if not isinstance(component_raw, dict):
            continue
        if not _is_distributable_python_component(component_raw):
            continue

        package = str(component_raw.get("name", "<unknown>")).strip().lower()
        for license_id in _component_licenses(component_raw):
            if not _is_banned(license_id):
                continue
            if _allowlisted(package, license_id, allowlist):
                continue
            errors.append(
                "banned license detected: "
                f"package={package} license={license_id} purl={component_raw.get('purl', '<none>')}"
            )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sbom", required=True, type=Path, help="Path to CycloneDX JSON SBOM")
    parser.add_argument(
        "--allowlist",
        required=True,
        type=Path,
        help="Path to JSON allowlist with expiry dates",
    )
    args = parser.parse_args(argv)

    errors = check_licenses(args.sbom, args.allowlist)
    if errors:
        for error in errors:
            print(f"license-check: {error}")
        print("license-check: FAILED")
        return 1

    print("license-check: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
