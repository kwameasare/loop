"""Eval harness domain models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ToolInvocation(BaseModel):
    """One tool call observed during an agent run, or expected by a sample.

    Args are kept as a JSON-encoded string so the model stays hashable and the
    type signature remains ``frozen+strict`` without resorting to immutable
    deep mappings. Scorers comparing arg sets parse the JSON on demand.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    name: str = Field(min_length=1)
    args_json: str = "{}"


class Sample(BaseModel):
    """One row of an eval dataset."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: str = Field(min_length=1)
    input: str
    expected: str | None = None
    expected_tool_calls: tuple[ToolInvocation, ...] = ()
    metadata: dict[str, str] = Field(default_factory=dict)


class Run(BaseModel):
    """Captures a single agent invocation outcome for one sample."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    sample_id: str = Field(min_length=1)
    output: str
    latency_ms: float = Field(ge=0)
    cost_usd: float = Field(ge=0)
    tool_calls: tuple[ToolInvocation, ...] = ()
    metadata: dict[str, str] = Field(default_factory=dict)


class Score(BaseModel):
    """A scorer's verdict for one run."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    scorer: str = Field(min_length=1)
    sample_id: str = Field(min_length=1)
    value: float = Field(ge=0.0, le=1.0)
    passed: bool
    detail: str = ""


class EvalReport(BaseModel):
    """The aggregate report for a single eval run."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    samples: int = Field(ge=0)
    runs: tuple[Run, ...]
    scores: tuple[Score, ...]
    pass_rate: float = Field(ge=0.0, le=1.0)
    mean_latency_ms: float = Field(ge=0)
    total_cost_usd: float = Field(ge=0)


__all__ = ["EvalReport", "Run", "Sample", "Score", "ToolInvocation"]
