"""Pass14 acceptance coverage for S410."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_multi_e2e_script_asserts_result_cost_and_trace() -> None:
    repo = Path(__file__).resolve().parents[3]
    proc = subprocess.run(
        [sys.executable, str(repo / "scripts" / "multi_e2e.py")],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(proc.stdout)
    assert summary["output"] == "billing: refund approved\nsupport: customer notified"
    assert summary["trace"] == [
        "supervisor",
        "__fanout__",
        "billing",
        "support",
        "__end__",
    ]
    assert summary["total_cost_usd"] == 0.006
    assert summary["child_trace_ids"] == [
        "00000000000000000000000000000002",
        "00000000000000000000000000000003",
    ]
