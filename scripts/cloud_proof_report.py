"""Append cross-cloud smoke marks to docs/CLOUD_PROOF.md."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

BEGIN = "<!-- CLOUD_PROOF_HISTORY:BEGIN -->"
END = "<!-- CLOUD_PROOF_HISTORY:END -->"


def _mark(status: str) -> str:
    status = status.lower()
    if status in {"success", "passed", "green"}:
        return "GREEN"
    if status in {"failure", "cancelled", "skipped", "timed_out", "red"}:
        return "RED"
    raise ValueError(f"unsupported cloud proof status: {status}")


def _text(raw: dict[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"cloud proof artifact missing {key}")
    return value


def _row(path: Path) -> str:
    raw = cast(dict[str, object], json.loads(path.read_text()))
    checked_at = _text(raw, "checked_at").replace("+00:00", "Z")
    cloud = _text(raw, "cloud")
    region = _text(raw, "region")
    mark = _mark(_text(raw, "mark"))
    run_url = _text(raw, "run_url")
    sha = _text(raw, "sha")
    return f"| {checked_at} | `{cloud}` | `{region}` | {mark} | [run]({run_url}) | `{sha}` |"


def append_marks(report: Path, artifacts: list[Path]) -> None:
    text = report.read_text()
    if BEGIN not in text or END not in text:
        raise ValueError(f"{report} is missing cloud proof history markers")
    if not artifacts:
        raise ValueError("at least one cloud proof artifact is required")
    before, rest = text.split(BEGIN, 1)
    current, after = rest.split(END, 1)
    rows = [line for line in current.splitlines() if line.startswith("| 20")]
    rows.extend(_row(path) for path in sorted(artifacts))
    rendered = "\n".join(rows[-42:])
    report.write_text(f"{before}{BEGIN}\n{rendered}\n{END}{after}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    mark = sub.add_parser("mark")
    for name in ("cloud", "region", "status", "run-url", "sha"):
        mark.add_argument(f"--{name}", required=True)
    mark.add_argument("--output", type=Path, required=True)
    append = sub.add_parser("append")
    append.add_argument("--report", type=Path, default=Path("docs/CLOUD_PROOF.md"))
    append.add_argument("artifacts", nargs="*", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "mark":
            payload = {
                "checked_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
                "cloud": cast(str, args.cloud),
                "region": cast(str, args.region),
                "mark": _mark(cast(str, args.status)),
                "run_url": cast(str, args.run_url),
                "sha": cast(str, args.sha)[:12],
            }
            cast(Path, args.output).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        else:
            append_marks(cast(Path, args.report), cast(list[Path], args.artifacts))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"cloud-proof-report: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
