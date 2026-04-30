"""Parallel eval-suite runner (S249).

Drives a dataset through ``EvalRunner`` semantics but with a bounded
concurrency cap, optional per-case timeout, and deterministic ordering of
the resulting ``EvalReport`` (sorted by sample id) regardless of completion
order.

Why a separate module: ``EvalRunner.run`` is sequential by design (good
default for laptop dev). The parallel runner is opt-in for CI and large
production-replay sweeps where the cost is dominated by upstream LLM
latency. Sharing internals would force the small runner to grow knobs it
doesn't need.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterable
from typing import cast

from loop_eval.models import EvalReport, Run, Sample, Score
from loop_eval.runner import AgentFn
from loop_eval.scorers import Scorer


class CaseTimeout(asyncio.TimeoutError):
    """Raised internally when a single case exceeds ``per_case_timeout_s``."""


class ParallelEvalRunner:
    """Bounded-concurrency, per-case-timeout aware runner."""

    def __init__(
        self,
        scorers: Iterable[Scorer],
        *,
        concurrency: int = 8,
        per_case_timeout_s: float | None = 30.0,
    ) -> None:
        self._scorers: tuple[Scorer, ...] = tuple(scorers)
        if not self._scorers:
            raise ValueError("at least one scorer is required")
        if concurrency < 1:
            raise ValueError("concurrency must be >= 1")
        if per_case_timeout_s is not None and per_case_timeout_s <= 0:
            raise ValueError("per_case_timeout_s must be > 0 when set")
        self._concurrency = concurrency
        self._timeout = per_case_timeout_s

    async def _run_one(
        self,
        sample: Sample,
        agent: AgentFn,
        sem: asyncio.Semaphore,
    ) -> Run:
        async with sem:
            t0 = time.perf_counter()
            try:
                if self._timeout is None:
                    output, cost = await agent(sample)
                else:
                    output, cost = await asyncio.wait_for(
                        agent(sample), timeout=self._timeout
                    )
            except TimeoutError:
                return Run(
                    sample_id=sample.id,
                    output="",
                    latency_ms=self._timeout * 1000 if self._timeout else 0.0,
                    cost_usd=0.0,
                    metadata={"timeout": "true"},
                )
            except Exception as exc:
                return Run(
                    sample_id=sample.id,
                    output="",
                    latency_ms=(time.perf_counter() - t0) * 1000,
                    cost_usd=0.0,
                    metadata={"error": type(exc).__name__, "detail": str(exc)},
                )
            return Run(
                sample_id=sample.id,
                output=output,
                latency_ms=(time.perf_counter() - t0) * 1000,
                cost_usd=cost,
            )

    async def run(
        self, *, dataset: Iterable[Sample], agent: AgentFn
    ) -> EvalReport:
        samples = list(dataset)
        sem = asyncio.Semaphore(self._concurrency)
        runs = await asyncio.gather(
            *(self._run_one(s, agent, sem) for s in samples)
        )
        # Stable ordering by sample id so the report is deterministic.
        sample_by_id = {s.id: s for s in samples}
        runs.sort(key=lambda r: r.sample_id)
        scores: list[Score] = []
        for run in runs:
            sample = sample_by_id[run.sample_id]
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


__all__ = ["CaseTimeout", "ParallelEvalRunner"]
