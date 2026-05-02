"""File a GitHub issue for any fuzz-harness crashes (S800).

Reads ``fuzz-report.json`` (produced by :mod:`tools.fuzz_harness`) and
calls ``gh issue create`` once per crash signature. Designed to run in
the nightly CI workflow after ``tools/fuzz_harness.py``. Idempotent
within a single run: identical signatures collapse to a single issue.

Usage::

    python tools/fuzz_report_to_issue.py --report fuzz-report.json [--dry-run]

When ``--dry-run`` is passed (or the ``GH_DRY_RUN`` env var is set, used
by CI smoke tests), the script prints the ``gh`` invocations instead of
executing them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _signature(crash: dict[str, Any]) -> str:
    """Stable hash of a crash so duplicates collapse to one issue."""
    trace = crash.get("trace", "")
    # Drop file-path prefixes so the same bug from /home/runner and
    # /Users/me hashes the same.
    normalised = "\n".join(
        line.split('File "')[-1].split(", line")[0].split("/")[-1] + " "
        + line.strip().split(", in ")[-1]
        if line.strip().startswith('File "')
        else line.strip()
        for line in trace.splitlines()
    )
    return hashlib.sha256(
        f"{crash.get('kind', '')}\n{normalised}".encode("utf-8")
    ).hexdigest()[:12]


def _format_issue(
    *, campaign: str, crash: dict[str, Any], signature: str
) -> tuple[str, str]:
    title = f"fuzz: {crash.get('kind', 'Crash')} in {campaign} ({signature})"
    body_lines = [
        "Detected by `tools/fuzz_harness.py` in the nightly fuzz run.",
        "",
        f"- Campaign: `{campaign}`",
        f"- Kind: `{crash.get('kind')}`",
        f"- Iteration: `{crash.get('iteration')}`",
        f"- Signature: `{signature}`",
        "",
        "## Trace",
        "```",
        crash.get("trace", "").rstrip(),
        "```",
    ]
    return title, "\n".join(body_lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path("fuzz-report.json"))
    parser.add_argument("--label", default="fuzz,security,nightly")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not args.report.is_file():
        print(f"no fuzz report at {args.report}", file=sys.stderr)
        return 0

    report = json.loads(args.report.read_text(encoding="utf-8"))
    seen: set[str] = set()
    filed = 0
    dry_run = args.dry_run or os.environ.get("GH_DRY_RUN") == "1"

    for camp in report.get("campaigns", []):
        for crash in camp.get("crashes", []):
            sig = _signature(crash)
            if sig in seen:
                continue
            seen.add(sig)
            title, body = _format_issue(
                campaign=camp.get("name", "?"), crash=crash, signature=sig
            )
            cmd = [
                "gh",
                "issue",
                "create",
                "--title",
                title,
                "--body",
                body,
                "--label",
                args.label,
            ]
            if dry_run or shutil.which("gh") is None:
                print("[dry-run]", " ".join(repr(c) for c in cmd))
            else:
                subprocess.run(cmd, check=True)  # noqa: S603 — args fully built.
            filed += 1

    print(f"filed {filed} fuzz issue(s); {len(seen)} unique signatures")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
