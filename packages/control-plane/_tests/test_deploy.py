from __future__ import annotations

from uuid import uuid4

import pytest
from loop_control_plane import (
    DeployArtifact,
    DeployController,
    DeployError,
    DeployPhase,
    InMemoryImageBuilder,
    InMemoryImageRegistry,
    InMemoryKubeClient,
)


def _artifact() -> DeployArtifact:
    return DeployArtifact(
        id=uuid4(),
        workspace_id=uuid4(),
        agent_id=uuid4(),
        version="1.0.0",
        source_digest="abcdef0123456789",
    )


@pytest.mark.asyncio
async def test_happy_path_runs_state_machine_to_ready() -> None:
    builder = InMemoryImageBuilder()
    registry = InMemoryImageRegistry()
    kube = InMemoryKubeClient()
    ctl = DeployController(builder=builder, registry=registry, kube=kube)

    deploy = await ctl.submit(_artifact())
    assert deploy.phase is DeployPhase.PENDING

    final = await ctl.run(deploy.id)
    assert final.phase is DeployPhase.READY
    assert final.image_ref is not None
    assert len(builder.builds) == 1
    assert len(registry.pushed) == 1
    assert len(kube.applied) == 1


@pytest.mark.asyncio
async def test_failure_during_build_marks_failed_with_error() -> None:
    async def boom(_: DeployArtifact) -> None:
        raise RuntimeError("buildkit ran out of disk")

    ctl = DeployController(
        builder=InMemoryImageBuilder(on_build=boom),
        registry=InMemoryImageRegistry(),
        kube=InMemoryKubeClient(),
    )
    d = await ctl.submit(_artifact())
    final = await ctl.run(d.id)
    assert final.phase is DeployPhase.FAILED
    assert final.error is not None
    assert "buildkit" in final.error


@pytest.mark.asyncio
async def test_run_is_idempotent_on_terminal_phases() -> None:
    ctl = DeployController(
        builder=InMemoryImageBuilder(),
        registry=InMemoryImageRegistry(),
        kube=InMemoryKubeClient(),
    )
    d = await ctl.submit(_artifact())
    first = await ctl.run(d.id)
    second = await ctl.run(d.id)
    assert first == second


@pytest.mark.asyncio
async def test_rollback_after_ready_calls_kube_and_records_phase() -> None:
    kube = InMemoryKubeClient()
    ctl = DeployController(
        builder=InMemoryImageBuilder(),
        registry=InMemoryImageRegistry(),
        kube=kube,
    )
    d = await ctl.submit(_artifact())
    await ctl.run(d.id)
    rolled = await ctl.rollback(d.id)
    assert rolled.phase is DeployPhase.ROLLED_BACK
    assert kube.rolled_back == [d.id]


@pytest.mark.asyncio
async def test_rollback_rejects_pending_and_unknown() -> None:
    ctl = DeployController(
        builder=InMemoryImageBuilder(),
        registry=InMemoryImageRegistry(),
        kube=InMemoryKubeClient(),
    )
    d = await ctl.submit(_artifact())
    with pytest.raises(DeployError):
        await ctl.rollback(d.id)
    with pytest.raises(DeployError):
        await ctl.get(uuid4())


@pytest.mark.asyncio
async def test_apply_failure_does_not_swallow_error() -> None:
    async def fail(_did, _ref):
        raise RuntimeError("kube apiserver 503")

    ctl = DeployController(
        builder=InMemoryImageBuilder(),
        registry=InMemoryImageRegistry(),
        kube=InMemoryKubeClient(on_apply=fail),
    )
    d = await ctl.submit(_artifact())
    final = await ctl.run(d.id)
    assert final.phase is DeployPhase.FAILED
    assert final.error is not None and "503" in final.error
