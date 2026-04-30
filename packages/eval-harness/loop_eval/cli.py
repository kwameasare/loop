"""``loop eval`` CLI (S251).

A small argparse-based entry point that:

* loads suites from a directory of YAML files,
* runs them through an agent the caller wires up,
* emits TAP 13 by default and ``--json`` machine-readable output on demand,
* exits 0 on full pass, 1 on any failure.

We intentionally don't ship a default agent: the eval harness has no way
to know which provider to call. Test/integrators install a Python entry
point that returns an ``AgentFn``; the CLI looks it up via
``--agent-factory module:callable``.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import sys
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loop_eval.models import EvalReport
from loop_eval.regression import (
    detect_regression,
    load_report,
    regression_to_dict,
)
from loop_eval.runner import AgentFn, EvalRunner
from loop_eval.scorers import Scorer, exact_match
from loop_eval.suite_loader import LoadedSuite, load_suite, load_suites

AgentFactory = Callable[[], Awaitable[AgentFn] | AgentFn]


@dataclass(frozen=True)
class _CliResult:
    suites: tuple[LoadedSuite, ...]
    reports: tuple[EvalReport, ...]
    regression_failed: bool


def _resolve_factory(spec: str) -> AgentFactory:
    if ":" not in spec:
        raise ValueError(
            "agent factory spec must be 'module:callable', got " + repr(spec)
        )
    mod_name, attr = spec.split(":", 1)
    module = importlib.import_module(mod_name)
    factory = getattr(module, attr)
    if not callable(factory):
        raise TypeError(f"{spec}: resolved object is not callable")
    return factory  # type: ignore[return-value]


async def _materialise_agent(factory: AgentFactory) -> AgentFn:
    result = factory()
    if asyncio.iscoroutine(result):
        result = await result
    return result  # type: ignore[return-value]


async def _run_async(
    *,
    suites: Sequence[LoadedSuite],
    agent: AgentFn,
    scorers: Sequence[Scorer],
) -> list[EvalReport]:
    runner = EvalRunner(scorers)
    out: list[EvalReport] = []
    for suite in suites:
        out.append(await runner.run(dataset=suite.samples, agent=agent))
    return out


def _emit_tap(
    suites: Sequence[LoadedSuite],
    reports: Sequence[EvalReport],
    out: Any,
) -> int:
    """Emit TAP-13 to ``out``; returns 0 if all green, 1 otherwise."""

    print("TAP version 13", file=out)
    total_cases = sum(r.samples for r in reports)
    print(f"1..{max(total_cases, 0)}", file=out)
    failed = 0
    case_no = 0
    for suite, report in zip(suites, reports, strict=True):
        # Group scores by sample id for human-readable output.
        by_sample: dict[str, list[Any]] = {}
        for s in report.scores:
            by_sample.setdefault(s.sample_id, []).append(s)
        for sample in suite.samples:
            case_no += 1
            scores = by_sample.get(sample.id, [])
            ok = bool(scores) and all(s.passed for s in scores)
            if not ok:
                failed += 1
            status = "ok" if ok else "not ok"
            print(
                f"{status} {case_no} - {suite.name}/{sample.id}",
                file=out,
            )
            for sc in scores:
                marker = "✓" if sc.passed else "✗"
                print(
                    f"  # {marker} {sc.scorer}: value={sc.value:.3f} "
                    f"detail={sc.detail!r}",
                    file=out,
                )
    if failed:
        print(f"# {failed} of {total_cases} cases failed", file=out)
        return 1
    return 0


def _emit_json(
    suites: Sequence[LoadedSuite],
    reports: Sequence[EvalReport],
    out: Any,
) -> int:
    payload = {
        "suites": [
            {
                "name": suite.name,
                "path": str(suite.path),
                "report": report.model_dump(mode="json"),
            }
            for suite, report in zip(suites, reports, strict=True)
        ]
    }
    json.dump(payload, out, indent=2, sort_keys=True)
    out.write("\n")
    failed = sum(1 for r in reports for s in r.scores if not s.passed)
    return 1 if failed else 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="loop eval", description="Run a Loop eval suite."
    )
    parser.add_argument(
        "suites",
        type=Path,
        help="Path to a YAML suite file or a directory of suites.",
    )
    parser.add_argument(
        "--agent-factory",
        required=True,
        help="Python entry point 'module:callable' returning an AgentFn.",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Optional baseline EvalReport JSON to gate regressions.",
    )
    parser.add_argument(
        "--regression-threshold",
        type=float,
        default=0.05,
        help="Relative drop threshold for declaring regression (default: 0.05).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output instead of TAP-13.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    suites: list[LoadedSuite] = (
        load_suites(args.suites)
        if args.suites.is_dir()
        else [load_suite(args.suites)]
    )

    factory = _resolve_factory(args.agent_factory)
    agent = asyncio.run(_materialise_agent(factory))
    reports = asyncio.run(
        _run_async(suites=suites, agent=agent, scorers=[exact_match])
    )

    out = sys.stdout
    rc = (
        _emit_json(suites, reports, out)
        if args.json
        else _emit_tap(suites, reports, out)
    )

    if args.baseline is not None and reports:
        baseline = load_report(args.baseline)
        # Regression is checked against the *first* suite for simplicity;
        # multi-suite baselines are deferred to S252.
        regression = detect_regression(
            baseline=baseline,
            current=reports[0],
            threshold=args.regression_threshold,
        )
        print("# regression: " + json.dumps(regression_to_dict(regression)))
        if regression.regressed:
            rc = 1
    return rc


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["main"]
