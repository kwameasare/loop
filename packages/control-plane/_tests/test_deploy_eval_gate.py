"""Tests for the eval-gated deploy regression block (S031)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from loop_control_plane import (
    DeployArtifact,
    DeployController,
    DeployError,
    DeployPhase,
    EvalReport,
    InMemoryBaselineRegistry,
    InMemoryEvalGate,
    InMemoryImageBuilder,
    InMemoryImageRegistry,
    InMemoryKubeClient,
)


def _artifact(workspace_id=None, agent_id=None) -> DeployArtifact:
    return DeployArtifact(
        id=uuid4(),
        workspace_id=workspace_id or uuid4(),
        agent_id=agent_id or uuid4(),
        version="1.0.0",
        source_digest="abcdef0123456789",
    )


def _ctl(*, gate, baselines):
    return DeployController(
        builder=InMemoryImageBuilder(),
        registry=InMemoryImageRegistry(),
        kube=InMemoryKubeClient(),
        eval_gate=gate,
        baselines=baselines,
    )


@pytest.mark.asyncio
async def test_first_deploy_has_no_baseline_and_records_pass_rate() -> None:
    gate = InMemoryEvalGate(pass_rates=[0.92])
    baselines = InMemoryBaselineRegistry()
    ctl = _ctl(gate=gate, baselines=baselines)
    artifact = _artifact()

    final = await ctl.run((await ctl.submit(artifact)).id)

    assert final.phase is DeployPhase.READY
    assert final.eval_report is not None
    assert final.eval_report.baseline_pass_rate is None
    assert final.eval_report.regression is False
    assert baselines.records == [
        (artifact.workspace_id, artifact.agent_id, 0.92)
    ]


@pytest.mark.asyncio
async def test_regression_blocks_promotion_with_typed_error() -> None:
    gate = InMemoryEvalGate(pass_rates=[0.95, 0.80])
    baselines = InMemoryBaselineRegistry()
    ws = uuid4()
    agent = uuid4()
    ctl = _ctl(gate=gate, baselines=baselines)

    # First deploy establishes baseline 0.95.
    first = await ctl.run(
        (await ctl.submit(_artifact(workspace_id=ws, agent_id=agent))).id
    )
    assert first.phase is DeployPhase.READY

    # Second deploy regresses to 0.80 -- gate must block.
    second = await ctl.run(
        (await ctl.submit(_artifact(workspace_id=ws, agent_id=agent))).id
    )
    assert second.phase is DeployPhase.FAILED
    assert second.error is not None
    assert "eval-regression" in second.error
    assert second.eval_report is not None
    assert second.eval_report.regression is True
    assert second.eval_report.baseline_pass_rate == pytest.approx(0.95)
    # Baseline is NOT updated by a failing candidate.
    assert baselines.records == [(ws, agent, 0.95)]


@pytest.mark.asyncio
async def test_equal_to_baseline_is_not_a_regression() -> None:
    gate = InMemoryEvalGate(pass_rates=[0.90, 0.90])
    baselines = InMemoryBaselineRegistry()
    ws = uuid4()
    agent = uuid4()
    ctl = _ctl(gate=gate, baselines=baselines)

    await ctl.run(
        (await ctl.submit(_artifact(workspace_id=ws, agent_id=agent))).id
    )
    second = await ctl.run(
        (await ctl.submit(_artifact(workspace_id=ws, agent_id=agent))).id
    )
    assert second.phase is DeployPhase.READY
    assert second.eval_report is not None
    assert second.eval_report.regression is False


@pytest.mark.asyncio
async def test_no_gate_means_no_evaluating_phase_and_no_baseline_io() -> None:
    ctl = DeployController(
        builder=InMemoryImageBuilder(),
        registry=InMemoryImageRegistry(),
        kube=InMemoryKubeClient(),
    )
    final = await ctl.run((await ctl.submit(_artifact())).id)
    assert final.phase is DeployPhase.READY
    assert final.eval_report is None


@pytest.mark.asyncio
async def test_gate_and_baselines_must_be_provided_together() -> None:
    with pytest.raises(DeployError):
        DeployController(
            builder=InMemoryImageBuilder(),
            registry=InMemoryImageRegistry(),
            kube=InMemoryKubeClient(),
            eval_gate=InMemoryEvalGate(pass_rates=[1.0]),
        )
    with pytest.raises(DeployError):
        DeployController(
            builder=InMemoryImageBuilder(),
            registry=InMemoryImageRegistry(),
            kube=InMemoryKubeClient(),
            baselines=InMemoryBaselineRegistry(),
        )


@pytest.mark.asyncio
async def test_eval_report_is_frozen_strict() -> None:
    from pydantic import ValidationError

    ok = EvalReport(
        pass_rate=0.5, total_cases=10, baseline_pass_rate=None, regression=False
    )
    with pytest.raises(ValidationError):
        ok.model_copy(update={"pass_rate": 2.0}).model_validate(
            ok.model_dump() | {"pass_rate": 2.0}
        )
    with pytest.raises(ValidationError):
        EvalReport(pass_rate=-0.1, total_cases=1)
    with pytest.raises(ValidationError):
        EvalReport(pass_rate=1.1, total_cases=1)
