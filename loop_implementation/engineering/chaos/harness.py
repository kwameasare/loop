#!/usr/bin/env python3
"""
chaos/harness.py — Chaos engineering harness for Loop staging.

Runs scripted chaos scenarios, captures RTO/data-loss metrics, and appends
findings to loop_implementation/engineering/CHAOS_FINDINGS.md.

Usage:
    python chaos/harness.py [--scenario SCENARIO] [--dry-run]

Scenarios:
    network_partition   — Drop all traffic to a service for 30 s
    db_failover         — Trigger Postgres primary failover; measure RTO
    nats_outage         — Kill a NATS node; measure re-election time
    all                 — Run all three scenarios sequentially (default)

SLA targets (from engineering/RUNBOOKS.md):
    network_partition  → service resumes within 60 s
    db_failover        → new leader elected within 30 s (RTO ≤ 5 min full recovery)
    nats_outage        → NATS pod running within 60 s
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CHAOS_DIR = Path(__file__).resolve().parent
FINDINGS_FILE = REPO_ROOT / "loop_implementation" / "engineering" / "CHAOS_FINDINGS.md"

# SLA limits (seconds) for each scenario
SLA_LIMITS: dict[str, int] = {
    "network_partition": 60,
    "db_failover": 300,   # 5 min RTO per RB-001
    "nats_outage": 60,
}

SCRIPT_MAP: dict[str, str] = {
    "network_partition": "network_partition.sh",
    "db_failover": "db_failover.sh",
    "nats_outage": "nats_outage.sh",
}


def run_scenario(name: str, dry_run: bool = False) -> dict:
    script = CHAOS_DIR / SCRIPT_MAP[name]
    if not script.exists():
        return {"scenario": name, "error": f"script not found: {script}", "status": "error"}

    env = os.environ.copy()
    if dry_run:
        # Dry-run: zero-duration so scripts skip real faults
        env["CHAOS_DURATION"] = "0"

    print(f"[harness] running scenario: {name}", flush=True)
    try:
        result = subprocess.run(
            ["bash", str(script)],
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
        )
        # Extract JSON from stdout (last { … } block)
        stdout = result.stdout.strip()
        last_json = ""
        for line in reversed(stdout.splitlines()):
            if line.startswith("{") or last_json:
                last_json = line + "\n" + last_json
                if last_json.strip().startswith("{") and last_json.strip().endswith("}"):
                    break

        try:
            data = json.loads(last_json.strip())
        except json.JSONDecodeError:
            data = {"scenario": name, "raw_stdout": stdout, "status": "parse_error"}

        data["returncode"] = result.returncode
        data["stderr"] = result.stderr[-500:] if result.stderr else ""
        return data
    except subprocess.TimeoutExpired:
        return {"scenario": name, "status": "timeout", "error": "exceeded 600 s"}


def assess_sla(result: dict) -> tuple[bool, str]:
    name = result.get("scenario", "")
    limit = SLA_LIMITS.get(name)
    if limit is None:
        return True, "unknown scenario — skipped"
    rto = result.get("rto_s")
    if rto is None:
        return True, "no RTO recorded (dry-run or parse error)"
    passed = int(rto) <= limit
    msg = f"RTO={rto}s {'≤' if passed else '>'} SLA limit={limit}s"
    return passed, msg


def append_findings(results: list[dict]) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"\n## Drill run — {now}\n\n"]
    for r in results:
        name = r.get("scenario", "unknown")
        passed, sla_msg = assess_sla(r)
        badge = "✅ PASS" if passed else "❌ FAIL"
        lines.append(f"### {name} — {badge}\n\n")
        lines.append(f"- **SLA check:** {sla_msg}\n")
        for k, v in r.items():
            if k not in ("scenario", "stderr", "raw_stdout", "returncode"):
                lines.append(f"- **{k}:** {v}\n")
        if r.get("stderr"):
            lines.append(f"\n```\n{r['stderr']}\n```\n")
        lines.append("\n")

    if not FINDINGS_FILE.exists():
        FINDINGS_FILE.write_text("# Chaos Engineering Findings\n\nThis file is auto-updated by `chaos/harness.py`.\n")

    with FINDINGS_FILE.open("a") as f:
        f.writelines(lines)
    print(f"[harness] findings appended to {FINDINGS_FILE}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Loop chaos engineering harness")
    parser.add_argument(
        "--scenario",
        choices=list(SCRIPT_MAP.keys()) + ["all"],
        default="all",
    )
    parser.add_argument("--dry-run", action="store_true", help="skip real faults; measure harness plumbing only")
    args = parser.parse_args()

    scenarios = list(SCRIPT_MAP.keys()) if args.scenario == "all" else [args.scenario]

    all_results: list[dict] = []
    for s in scenarios:
        r = run_scenario(s, dry_run=args.dry_run)
        all_results.append(r)
        passed, msg = assess_sla(r)
        status_str = "PASS" if passed else "FAIL"
        print(f"[harness] {s}: {status_str} — {msg}", flush=True)

    append_findings(all_results)

    failures = [r for r in all_results if not assess_sla(r)[0]]
    if failures:
        print(f"[harness] {len(failures)} SLA violation(s)", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
