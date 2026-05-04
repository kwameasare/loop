"""Unit checks for tools/check_audit_allowlist_expiry.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_audit_allowlist_expiry as checker  # type: ignore[import-not-found]


def test_expired_entries_fail_validation(tmp_path: Path) -> None:
    pip_allow = tmp_path / "pip_audit_allow.txt"
    npm_allow = tmp_path / "npm_audit_allow.json"

    pip_allow.write_text("CVE-2026-0001|2000-01-01|expired\n", encoding="utf-8")
    npm_allow.write_text(
        json.dumps(
            {
                "allow": [
                    {
                        "id": "1001",
                        "expires": "2000-01-01",
                        "reason": "expired",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    pip_records, pip_errors = checker.load_pip_allowlist(pip_allow)
    npm_records, npm_errors = checker.load_npm_allowlist(npm_allow)

    assert pip_records
    assert npm_records
    assert any("expired pip allowlist entry" in err for err in pip_errors)
    assert any("expired npm allowlist entry" in err for err in npm_errors)


def test_pip_report_blocks_unallowlisted_vulnerabilities(tmp_path: Path) -> None:
    pip_allow = tmp_path / "pip_audit_allow.txt"
    npm_allow = tmp_path / "npm_audit_allow.json"
    pip_report = tmp_path / "pip.json"

    pip_allow.write_text("CVE-2026-0001|2099-01-01|tracked\n", encoding="utf-8")
    npm_allow.write_text('{"allow": []}', encoding="utf-8")
    pip_report.write_text(
        json.dumps(
            [
                {
                    "name": "pkg-a",
                    "version": "1.0.0",
                    "vulns": [
                        {"id": "CVE-2026-0001"},
                        {"id": "CVE-2026-0002"},
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    pip_records, _ = checker.load_pip_allowlist(pip_allow)
    npm_records, _ = checker.load_npm_allowlist(npm_allow)
    errors = checker.evaluate_reports(
        pip_report_path=pip_report,
        npm_report_path=None,
        pip_allow=pip_records,
        npm_allow=npm_records,
        npm_threshold="high",
    )

    assert "unallowlisted pip vulnerability: CVE-2026-0002" in errors
    assert "unallowlisted pip vulnerability: CVE-2026-0001" not in errors


def test_npm_report_blocks_high_severity_unallowlisted_vulns(tmp_path: Path) -> None:
    pip_allow = tmp_path / "pip_audit_allow.txt"
    npm_allow = tmp_path / "npm_audit_allow.json"
    npm_report = tmp_path / "npm.json"

    pip_allow.write_text("", encoding="utf-8")
    npm_allow.write_text(
        json.dumps(
            {
                "allow": [
                    {
                        "id": "1001",
                        "expires": "2099-01-01",
                        "reason": "tracked",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    npm_report.write_text(
        json.dumps(
            {
                "auditReportVersion": 2,
                "vulnerabilities": {
                    "ansi-regex": {
                        "severity": "high",
                        "via": [
                            {
                                "source": 1001,
                                "severity": "high",
                            },
                            {
                                "source": 1002,
                                "severity": "critical",
                            },
                        ],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    pip_records, _ = checker.load_pip_allowlist(pip_allow)
    npm_records, _ = checker.load_npm_allowlist(npm_allow)
    errors = checker.evaluate_reports(
        pip_report_path=None,
        npm_report_path=npm_report,
        pip_allow=pip_records,
        npm_allow=npm_records,
        npm_threshold="high",
    )

    assert "unallowlisted npm vulnerability: 1002" in errors
    assert "unallowlisted npm vulnerability: 1001" not in errors
