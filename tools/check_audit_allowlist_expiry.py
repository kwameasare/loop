#!/usr/bin/env python3
"""Validate audit allowlist expiry dates and enforce pip/npm audit reports."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SEVERITY_ORDER = {
    "low": 1,
    "moderate": 2,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


@dataclass(frozen=True)
class AllowRecord:
    vuln_id: str
    expires: dt.date
    reason: str


def _parse_date(raw: str) -> dt.date:
    return dt.date.fromisoformat(raw)


def load_pip_allowlist(path: Path) -> tuple[dict[str, AllowRecord], list[str]]:
    records: dict[str, AllowRecord] = {}
    errors: list[str] = []
    today = dt.date.today()

    if not path.exists():
        return records, [f"pip allowlist file does not exist: {path}"]

    for index, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split("|", 2)]
        if len(parts) != 3:
            errors.append(f"invalid pip allowlist line {index}: {raw_line!r}")
            continue
        vuln_id, expires_raw, reason = parts
        if not vuln_id:
            errors.append(f"pip allowlist line {index} has empty vuln id")
            continue
        try:
            expires = _parse_date(expires_raw)
        except ValueError as exc:
            errors.append(f"pip allowlist line {index} has invalid expiry {expires_raw!r}: {exc}")
            continue
        if expires < today:
            errors.append(
                f"expired pip allowlist entry line {index}: {vuln_id} expired {expires.isoformat()}"
            )
        records[vuln_id] = AllowRecord(vuln_id=vuln_id, expires=expires, reason=reason)
    return records, errors


def load_npm_allowlist(path: Path) -> tuple[dict[str, AllowRecord], list[str]]:
    records: dict[str, AllowRecord] = {}
    errors: list[str] = []
    today = dt.date.today()

    if not path.exists():
        return records, [f"npm allowlist file does not exist: {path}"]

    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("allow", [])
    if not isinstance(entries, list):
        return records, ["npm allowlist field 'allow' must be a list"]

    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            errors.append(f"invalid npm allowlist entry {index}: {entry!r}")
            continue
        vuln_id = str(entry.get("id", "")).strip()
        expires_raw = str(entry.get("expires", "")).strip()
        reason = str(entry.get("reason", "")).strip()
        if not vuln_id or not expires_raw:
            errors.append(f"npm allowlist entry {index} missing id/expires")
            continue
        try:
            expires = _parse_date(expires_raw)
        except ValueError as exc:
            errors.append(f"npm allowlist entry {index} has invalid expiry {expires_raw!r}: {exc}")
            continue
        if expires < today:
            errors.append(
                f"expired npm allowlist entry {index}: {vuln_id} expired {expires.isoformat()}"
            )
        records[vuln_id] = AllowRecord(vuln_id=vuln_id, expires=expires, reason=reason)
    return records, errors


def _pip_vuln_ids(report: Any) -> set[str]:
    dependencies: list[Any]
    if isinstance(report, list):
        dependencies = report
    elif isinstance(report, dict):
        deps = report.get("dependencies")
        dependencies = deps if isinstance(deps, list) else []
    else:
        dependencies = []

    ids: set[str] = set()
    for dep in dependencies:
        if not isinstance(dep, dict):
            continue
        vulns = dep.get("vulns")
        if not isinstance(vulns, list):
            continue
        for vuln in vulns:
            if not isinstance(vuln, dict):
                continue
            vuln_id = vuln.get("id")
            if isinstance(vuln_id, str) and vuln_id:
                ids.add(vuln_id)
    return ids


def _severity_at_least(value: str, threshold: str) -> bool:
    return SEVERITY_ORDER.get(value.lower(), 0) >= SEVERITY_ORDER.get(threshold.lower(), 0)


def _npm_vuln_ids(report: Any, *, threshold: str) -> set[str]:
    vulnerabilities = {}
    if isinstance(report, dict):
        maybe = report.get("vulnerabilities")
        if isinstance(maybe, dict):
            vulnerabilities = maybe

    ids: set[str] = set()
    for pkg, payload in vulnerabilities.items():
        if not isinstance(payload, dict):
            continue
        severity = str(payload.get("severity", "")).lower()
        if not _severity_at_least(severity, threshold):
            continue

        via = payload.get("via")
        if isinstance(via, list) and via:
            for via_item in via:
                if isinstance(via_item, str):
                    ids.add(via_item)
                elif isinstance(via_item, dict):
                    via_severity = str(via_item.get("severity", severity)).lower()
                    if not _severity_at_least(via_severity, threshold):
                        continue
                    source = via_item.get("source")
                    name = via_item.get("name")
                    if source is not None:
                        ids.add(str(source))
                    elif isinstance(name, str) and name:
                        ids.add(name)
                    else:
                        ids.add(str(pkg))
        else:
            ids.add(str(pkg))
    return ids


def evaluate_reports(
    *,
    pip_report_path: Path | None,
    npm_report_path: Path | None,
    pip_allow: dict[str, AllowRecord],
    npm_allow: dict[str, AllowRecord],
    npm_threshold: str,
) -> list[str]:
    errors: list[str] = []

    if pip_report_path is not None:
        report = json.loads(pip_report_path.read_text(encoding="utf-8"))
        unresolved = sorted(v for v in _pip_vuln_ids(report) if v not in pip_allow)
        for vuln_id in unresolved:
            errors.append(f"unallowlisted pip vulnerability: {vuln_id}")

    if npm_report_path is not None:
        report = json.loads(npm_report_path.read_text(encoding="utf-8"))
        unresolved = sorted(v for v in _npm_vuln_ids(report, threshold=npm_threshold) if v not in npm_allow)
        for vuln_id in unresolved:
            errors.append(f"unallowlisted npm vulnerability: {vuln_id}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pip-allowlist", type=Path, default=Path("pip_audit_allow.txt"))
    parser.add_argument("--npm-allowlist", type=Path, default=Path("tools/npm_audit_allow.json"))
    parser.add_argument("--pip-report", type=Path, default=None)
    parser.add_argument("--npm-report", type=Path, default=None)
    parser.add_argument("--npm-audit-level", default="high")
    args = parser.parse_args(argv)

    pip_allow, pip_errors = load_pip_allowlist(args.pip_allowlist)
    npm_allow, npm_errors = load_npm_allowlist(args.npm_allowlist)

    errors = [*pip_errors, *npm_errors]
    errors.extend(
        evaluate_reports(
            pip_report_path=args.pip_report,
            npm_report_path=args.npm_report,
            pip_allow=pip_allow,
            npm_allow=npm_allow,
            npm_threshold=args.npm_audit_level,
        )
    )

    if errors:
        for error in errors:
            print(f"audit-allowlist: {error}")
        print("audit-allowlist: FAILED")
        return 1

    print("audit-allowlist: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
