"""Loop eval harness.

Public surface:

* `Sample`, `Score`, `Run`, `EvalReport` -- domain models.
* `Scorer` Protocol + 6 built-in scorers:
  ``exact_match``, ``regex_match``, ``json_schema``, ``llm_judge``,
  ``latency``, ``cost``.
* `EvalRunner` -- iterates a dataset, calls the agent fn, applies
  the configured scorers, returns a normalised `EvalReport`.
"""

from loop_eval.models import EvalReport, Run, Sample, Score
from loop_eval.runner import AgentFn, EvalRunner
from loop_eval.scorers import (
    JudgeFn,
    Scorer,
    cost_scorer,
    exact_match,
    json_schema_scorer,
    latency_scorer,
    llm_judge,
    regex_match,
)

__all__ = [
    "AgentFn",
    "EvalReport",
    "EvalRunner",
    "JudgeFn",
    "Run",
    "Sample",
    "Score",
    "Scorer",
    "cost_scorer",
    "exact_match",
    "json_schema_scorer",
    "latency_scorer",
    "llm_judge",
    "regex_match",
]
