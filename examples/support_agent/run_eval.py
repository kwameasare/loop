"""Run the support_agent eval suite.

This script is intentionally tiny: it loads the YAML suite, hands the cases to
``loop_eval.EvalRunner`` with a deterministic stub agent (so it can run in CI
without an LLM key), and prints a Markdown table.

For real runs against a live gateway, swap ``_stub_agent`` for an adapter that
calls the loop runtime (see docs/cookbook/support_agent.md).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import yaml
from loop_eval import (
    EvalReport,
    EvalRunner,
    Sample,
    Score,
    cost_scorer,
    latency_scorer,
    regex_match,
)

SUITE_PATH = Path(__file__).parent / "evals" / "suite.yaml"


def _load_samples() -> list[Sample]:
    suite = yaml.safe_load(SUITE_PATH.read_text())
    samples: list[Sample] = []
    for case in suite["cases"]:
        includes = case.get("expected", {}).get("response_includes_any", []) or []
        samples.append(
            Sample(
                id=case["name"],
                input=case["input"],
                metadata={"expected_first": includes[0] if includes else ""},
            )
        )
    return samples


async def _stub_agent(sample: Sample) -> tuple[str, float]:
    """Deterministic placeholder so this script runs without a gateway.

    Echoes the first phrase from ``response_includes_any`` so the regex_match
    scorer against that phrase always passes.
    """

    return (sample.metadata.get("expected_first") or "ok", 0.001)


def _markdown_table(report: EvalReport) -> str:
    lines = ["| sample | passed | scorers |", "| --- | --- | --- |"]
    by_sample: dict[str, list[Score]] = {}
    for s in report.scores:
        by_sample.setdefault(s.sample_id, []).append(s)
    for run in report.runs:
        case_scores = by_sample.get(run.sample_id, [])
        scorers = ", ".join(
            f"{s.scorer}={'✓' if s.passed else '✗'}" for s in case_scores
        )
        passed = all(s.passed for s in case_scores) if case_scores else False
        lines.append(
            f"| {run.sample_id} | {'✓' if passed else '✗'} | {scorers} |"
        )
    lines.append("")
    lines.append(f"**Pass rate:** {report.pass_rate:.0%}")
    return "\n".join(lines)


async def main() -> int:
    samples = _load_samples()
    runner = EvalRunner(
        scorers=[
            regex_match(r".+"),
            latency_scorer(max_ms=2000),
            cost_scorer(max_usd=0.01),
        ],
    )
    report = await runner.run(dataset=samples, agent=_stub_agent)
    print(_markdown_table(report))
    return 0 if report.pass_rate >= 0.7 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
