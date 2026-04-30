"""Loop eval harness.

Public surface:

* `Sample`, `Score`, `Run`, `EvalReport` -- domain models.
* `Scorer` Protocol + 6 built-in scorers:
  ``exact_match``, ``regex_match``, ``json_schema``, ``llm_judge``,
  ``latency``, ``cost``.
* `EvalRunner` -- iterates a dataset, calls the agent fn, applies
  the configured scorers, returns a normalised `EvalReport`.
"""

from loop_eval.cassettes import (
    CassetteEntry,
    CassetteMiss,
    CassetteRecorder,
    CassetteReplayer,
    load_cassette,
    parse_entry,
    request_key,
    serialise_entry,
)
from loop_eval.models import EvalReport, Run, Sample, Score, ToolInvocation
from loop_eval.parallel_runner import CaseTimeout, ParallelEvalRunner
from loop_eval.registry import (
    DuplicateSuiteError,
    EvalRegistry,
    EvalSuite,
    InMemoryEvalRegistry,
    SuiteNotFoundError,
    builtin_suites,
    default_registry,
)
from loop_eval.regression import (
    RegressionReport,
    SampleFlip,
    ScorerDelta,
    detect_regression,
    dump_report,
    load_report,
    regression_to_dict,
)
from loop_eval.replay import (
    FailedTurn,
    InMemoryReplaySink,
    ReplaySink,
    capture,
    should_capture,
    to_samples,
)
from loop_eval.runner import AgentFn, EvalRunner
from loop_eval.scorers import (
    JudgeFn,
    Scorer,
    bleu_scorer,
    cost_scorer,
    exact_match,
    json_schema_scorer,
    latency_scorer,
    llm_judge,
    regex_match,
    rouge_l,
    tool_call_match,
)
from loop_eval.suite_loader import (
    LoadedSuite,
    SuiteLoadError,
    load_suite,
    load_suites,
)

__all__ = [
    "AgentFn",
    "CaseTimeout",
    "CassetteEntry",
    "CassetteMiss",
    "CassetteRecorder",
    "CassetteReplayer",
    "DuplicateSuiteError",
    "EvalRegistry",
    "EvalReport",
    "EvalRunner",
    "EvalSuite",
    "FailedTurn",
    "InMemoryEvalRegistry",
    "InMemoryReplaySink",
    "JudgeFn",
    "LoadedSuite",
    "ParallelEvalRunner",
    "RegressionReport",
    "ReplaySink",
    "Run",
    "Sample",
    "SampleFlip",
    "Score",
    "Scorer",
    "ScorerDelta",
    "SuiteLoadError",
    "SuiteNotFoundError",
    "ToolInvocation",
    "bleu_scorer",
    "builtin_suites",
    "capture",
    "cost_scorer",
    "default_registry",
    "detect_regression",
    "dump_report",
    "exact_match",
    "json_schema_scorer",
    "latency_scorer",
    "llm_judge",
    "load_cassette",
    "load_report",
    "load_suite",
    "load_suites",
    "parse_entry",
    "regex_match",
    "regression_to_dict",
    "request_key",
    "rouge_l",
    "serialise_entry",
    "should_capture",
    "to_samples",
    "tool_call_match",
]
