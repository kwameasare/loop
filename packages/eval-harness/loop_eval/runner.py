"""Eval runner: invoke an agent against a dataset, score the runs."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable, Iterable
from typing import cast

from loop_eval.models import EvalReport, Run, Sample, Score
from loop_eval.scorers import Scorer

# An agent function takes a sample and returns ``(output, cost_usd)``.
# Latency is measured by the runner so callers can't inflate it.
AgentFn = Callable[[Sample], Awaitable[tuple[str, float]]]


class EvalRunner:
    def __init__(self, scorers: Iterable[Scorer]) -> None:
        self._scorers: tuple[Scorer, ...] = tuple(scorers)
        if not self._scorers:
            raise ValueError("at least one scorer is required")

    async def run(self, *, dataset: Iterable[Sample], agent: AgentFn) -> EvalReport:
        runs: list[Run] = []
        scores: list[Score] = []
        for sample in dataset:
            t0 = time.perf_counter()
            output, cost = await agent(sample)
            latency_ms = (time.perf_counter() - t0) * 1000
            run = Run(
                sample_id=sample.id,
                output=output,
                latency_ms=latency_ms,
                cost_usd=cost,
            )
            runs.append(run)
            for scorer in self._scorers:
                scores.append(cast(Score, scorer(sample, run)))

        n_runs = len(runs)
        if n_runs == 0:
            return EvalReport(
                samples=0,
                runs=(),
                scores=(),
                pass_rate=0.0,
                mean_latency_ms=0.0,
                total_cost_usd=0.0,
            )
        passed = sum(1 for s in scores if s.passed)
        pass_rate = passed / len(scores) if scores else 0.0
        mean_latency = sum(r.latency_ms for r in runs) / n_runs
        total_cost = sum(r.cost_usd for r in runs)
        return EvalReport(
            samples=n_runs,
            runs=tuple(runs),
            scores=tuple(scores),
            pass_rate=pass_rate,
            mean_latency_ms=mean_latency,
            total_cost_usd=total_cost,
        )


__all__ = ["AgentFn", "EvalRunner"]
