#!/usr/bin/env python3
"""Stamp the runbook index "Last drilled" cell for a given runbook ID."""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path


def stamp_runbook_date(path: Path, runbook_id: str, drilled_date: str) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    updated = False

    for idx, line in enumerate(lines):
        if not line.startswith(f"| {runbook_id} |"):
            continue
        parts = line.split("|")
        if len(parts) < 6:
            raise ValueError(f"malformed runbook index row: {line!r}")
        parts[4] = f" {drilled_date} (ci) "
        lines[idx] = "|".join(parts)
        updated = True
        break

    if not updated:
        raise ValueError(f"runbook row not found: {runbook_id}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runbook-id", required=True)
    parser.add_argument(
        "--date",
        default=dt.date.today().isoformat(),
        help="Drill date in YYYY-MM-DD format (defaults to today)",
    )
    parser.add_argument(
        "--runbooks-file",
        type=Path,
        default=Path("loop_implementation/engineering/RUNBOOKS.md"),
    )
    args = parser.parse_args(argv)

    try:
        dt.date.fromisoformat(args.date)
    except ValueError as exc:
        print(f"stamp-runbook: invalid --date {args.date!r}: {exc}")
        return 2

    stamp_runbook_date(args.runbooks_file, args.runbook_id, args.date)
    print(f"stamp-runbook: updated {args.runbook_id} -> {args.date} (ci)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
