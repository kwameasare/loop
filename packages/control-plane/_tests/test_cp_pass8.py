"""Tests for control-plane pass8 modules: dockerfile_render, canary,
deploy_events, trace_search, and a deploy + canary + events e2e (S271)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from loop_control_plane.canary import (
    STAGE_TRAFFIC,
    CanaryDecision,
    CanaryEventKind,
    CanaryFSM,
    CanaryHealth,
    CanaryPolicy,
    CanaryStage,
)
from loop_control_plane.deploy import (
    DeployArtifact,
    DeployController,
    DeployPhase,
    InMemoryBaselineRegistry,
    InMemoryEvalGate,
    InMemoryImageBuilder,
    InMemoryImageRegistry,
    InMemoryKubeClient,
)
from loop_control_plane.deploy_events import (
    DeployEvent,
    DeployEventKind,
    DeployEventStream,
    InMemoryDeployEventSink,
    deploy_to_event,
)
from loop_control_plane.dockerfile_render import (
    DEFAULT_RUNTIME_IMAGE,
    DockerfileSpec,
    render_dockerfile,
)
from loop_control_plane.trace_search import (
    InMemoryTraceStore,
    TraceQuery,
    TraceSearchService,
    TraceSummary,
)
from pydantic import ValidationError

# ---- dockerfile_render (S262) ----------------------------------------------


def _spec(**overrides: object) -> DockerfileSpec:
    base: dict[str, object] = {
        "service": "cp-api",
        "package_dir": "packages/control-plane",
        "entrypoint_module": "loop_control_plane.app",
    }
    base.update(overrides)
    return DockerfileSpec(**base)  # type: ignore[arg-type]


def test_dockerfile_default_runtime_distroless() -> None:
    out = render_dockerfile(_spec())
    assert "FROM python:3.14-slim-bookworm AS builder" in out
    assert f"FROM {DEFAULT_RUNTIME_IMAGE}" in out
    assert "USER nonroot" in out
    assert 'ENTRYPOINT ["python", "-m", "loop_control_plane.app"]' in out


def test_dockerfile_rejects_non_distroless_runtime() -> None:
    with pytest.raises(ValidationError):
        _spec(runtime_image="alpine:3.20")


def test_dockerfile_accepts_chainguard_runtime() -> None:
    spec = _spec(runtime_image="cgr.dev/chainguard/python:3.14")
    out = render_dockerfile(spec)
    assert "cgr.dev/chainguard/python:3.14" in out


def test_dockerfile_rejects_bad_service_slug() -> None:
    with pytest.raises(ValidationError):
        _spec(service="CP-API")  # uppercase fails [a-z]


def test_dockerfile_apt_block_sorted() -> None:
    out = render_dockerfile(_spec(extra_apt_packages=("libffi-dev", "ca-certificates")))
    # Sorted alphabetical
    assert "ca-certificates libffi-dev" in out


def test_dockerfile_expose_port() -> None:
    out = render_dockerfile(_spec(expose_port=8080))
    assert "EXPOSE 8080" in out


# ---- canary FSM (S267) ------------------------------------------------------


def _now() -> datetime:
    return datetime(2026, 5, 26, 4, 0, 0, tzinfo=UTC)


def _good() -> CanaryHealth:
    return CanaryHealth(samples=200, error_rate=0.005, p95_latency_ms=900)


def _too_few() -> CanaryHealth:
    return CanaryHealth(samples=50, error_rate=0.005, p95_latency_ms=900)


def _bad_errors() -> CanaryHealth:
    return CanaryHealth(samples=200, error_rate=0.10, p95_latency_ms=900)


def test_canary_full_promotion() -> None:
    fsm = CanaryFSM()
    d1 = fsm.step(_good(), now=_now())
    assert d1.stage is CanaryStage.CANARY_10
    assert d1.traffic_pct == STAGE_TRAFFIC[CanaryStage.CANARY_10]
    d2 = fsm.step(_good(), now=_now() + timedelta(minutes=5))
    assert d2.stage is CanaryStage.CANARY_50
    d3 = fsm.step(_good(), now=_now() + timedelta(minutes=10))
    assert d3.stage is CanaryStage.PROMOTED
    assert d3.terminal is True
    assert d3.traffic_pct == 100


def test_canary_insufficient_samples_holds_stage() -> None:
    fsm = CanaryFSM()
    d = fsm.step(_too_few(), now=_now())
    assert d.stage is CanaryStage.PROVISIONED
    assert d.event.kind is CanaryEventKind.INSUFFICIENT_SAMPLES
    assert d.terminal is False


def test_canary_regression_bypasses_min_samples() -> None:
    fsm = CanaryFSM()
    # Even with too-few samples, a blowup rolls back immediately.
    d = fsm.step(
        CanaryHealth(samples=10, error_rate=0.5, p95_latency_ms=200),
        now=_now(),
    )
    assert d.stage is CanaryStage.ROLLED_BACK
    assert d.terminal is True
    assert d.event.kind is CanaryEventKind.REGRESSION


def test_canary_force_rollback() -> None:
    fsm = CanaryFSM()
    fsm.step(_good(), now=_now())  # advance to CANARY_10
    d = fsm.force_rollback(reason="manual", now=_now() + timedelta(minutes=2))
    assert d.stage is CanaryStage.ROLLED_BACK
    assert d.terminal is True
    assert d.event.reason == "manual"


def test_canary_terminal_idempotent() -> None:
    fsm = CanaryFSM(policy=CanaryPolicy(min_samples=1))
    fsm.step(_good())
    fsm.step(_good())
    fsm.step(_good())
    assert fsm.stage is CanaryStage.PROMOTED
    d = fsm.step(_good())
    assert d.event.kind is CanaryEventKind.NO_CHANGE
    assert d.stage is CanaryStage.PROMOTED


def test_canary_p95_breach_rolls_back() -> None:
    fsm = CanaryFSM()
    d = fsm.step(
        CanaryHealth(samples=200, error_rate=0.0, p95_latency_ms=5000),
        now=_now(),
    )
    assert d.stage is CanaryStage.ROLLED_BACK


# ---- deploy_events (S269) ---------------------------------------------------


def test_deploy_event_to_row() -> None:
    workspace_id, deploy_id, agent_id = uuid4(), uuid4(), uuid4()
    ev = DeployEvent(
        workspace_id=workspace_id,
        deploy_id=deploy_id,
        agent_id=agent_id,
        kind=DeployEventKind.PHASE_CHANGED,
        from_stage="building",
        to_stage="pushing",
        reason="ok",
        image_ref=None,
        pass_rate=None,
        at=_now(),
    )
    row = ev.to_row()
    assert row["workspace_id"] == str(workspace_id)
    assert row["kind"] == "phase_changed"
    assert row["pass_rate"] is None
    assert row["at"] == _now().isoformat()


@pytest.mark.asyncio
async def test_deploy_event_stream_batches() -> None:
    sink = InMemoryDeployEventSink()
    stream = DeployEventStream(sink, batch_size=2)
    workspace_id, deploy_id, agent_id = uuid4(), uuid4(), uuid4()

    def make(k: DeployEventKind) -> DeployEvent:
        return deploy_to_event(
            workspace_id=workspace_id,
            deploy_id=deploy_id,
            agent_id=agent_id,
            kind=k,
            at=_now(),
        )

    await stream.emit(make(DeployEventKind.SUBMITTED))
    assert sink.events == []  # not flushed yet
    await stream.emit(make(DeployEventKind.PHASE_CHANGED))
    assert len(sink.events) == 2  # batch flushed at threshold
    await stream.emit(make(DeployEventKind.PHASE_CHANGED))
    await stream.aclose()
    assert len(sink.events) == 3


def test_deploy_event_stream_rejects_zero_batch() -> None:
    with pytest.raises(ValueError):
        DeployEventStream(InMemoryDeployEventSink(), batch_size=0)


def test_deploy_to_event_validates_extras_types() -> None:
    workspace_id, deploy_id, agent_id = uuid4(), uuid4(), uuid4()
    with pytest.raises(TypeError):
        deploy_to_event(
            workspace_id=workspace_id,
            deploy_id=deploy_id,
            agent_id=agent_id,
            kind=DeployEventKind.SUBMITTED,
            at=_now(),
            extras={"image_ref": 42},
        )


def test_in_memory_sink_filter() -> None:
    sink = InMemoryDeployEventSink()
    w1, w2, d1, d2, a = uuid4(), uuid4(), uuid4(), uuid4(), uuid4()
    e1 = DeployEvent(
        workspace_id=w1,
        deploy_id=d1,
        agent_id=a,
        kind=DeployEventKind.SUBMITTED,
        at=_now(),
    )
    e2 = DeployEvent(
        workspace_id=w2,
        deploy_id=d2,
        agent_id=a,
        kind=DeployEventKind.SUBMITTED,
        at=_now(),
    )
    sink.events.extend([e1, e2])
    assert sink.filter(workspace_id=w1) == [e1]
    assert sink.filter(deploy_id=d2) == [e2]


# ---- trace search (S287) ----------------------------------------------------


def _trace(
    ws: UUID,
    *,
    minute: int,
    error: bool = False,
    turn_id: UUID | None = None,
    agent_id: UUID | None = None,
) -> TraceSummary:
    return TraceSummary(
        workspace_id=ws,
        trace_id=f"{minute:032x}",
        turn_id=turn_id or uuid4(),
        conversation_id=uuid4(),
        agent_id=agent_id or uuid4(),
        started_at=datetime(2026, 5, 26, 4, minute, 0, tzinfo=UTC),
        duration_ms=100 + minute,
        span_count=3,
        error=error,
    )


@pytest.mark.asyncio
async def test_trace_search_filters_by_workspace() -> None:
    w1, w2 = uuid4(), uuid4()
    store = InMemoryTraceStore([_trace(w1, minute=10), _trace(w2, minute=20)])
    svc = TraceSearchService(store)
    res = await svc.run(TraceQuery(workspace_id=w1))
    assert len(res.items) == 1
    assert res.items[0].workspace_id == w1


@pytest.mark.asyncio
async def test_trace_search_pagination() -> None:
    ws = uuid4()
    store = InMemoryTraceStore([_trace(ws, minute=m) for m in range(1, 8)])
    svc = TraceSearchService(store)
    page1 = await svc.run(TraceQuery(workspace_id=ws, page_size=3))
    assert len(page1.items) == 3
    assert page1.next_cursor is not None
    page2 = await svc.run(
        TraceQuery(workspace_id=ws, page_size=3, cursor=page1.next_cursor)
    )
    assert len(page2.items) == 3
    page3 = await svc.run(
        TraceQuery(workspace_id=ws, page_size=3, cursor=page2.next_cursor)
    )
    assert len(page3.items) == 1
    assert page3.next_cursor is None


@pytest.mark.asyncio
async def test_trace_search_only_errors_filter() -> None:
    ws = uuid4()
    store = InMemoryTraceStore(
        [
            _trace(ws, minute=1),
            _trace(ws, minute=2, error=True),
            _trace(ws, minute=3),
        ]
    )
    svc = TraceSearchService(store)
    res = await svc.run(TraceQuery(workspace_id=ws, only_errors=True))
    assert len(res.items) == 1
    assert res.items[0].error is True


def test_trace_query_window_validator() -> None:
    ws = uuid4()
    with pytest.raises(ValidationError):
        TraceQuery(
            workspace_id=ws,
            started_at_from=datetime(2026, 5, 27, tzinfo=UTC),
            started_at_to=datetime(2026, 5, 26, tzinfo=UTC),
        )


def test_trace_query_page_size_bounds() -> None:
    ws = uuid4()
    with pytest.raises(ValidationError):
        TraceQuery(workspace_id=ws, page_size=0)
    with pytest.raises(ValidationError):
        TraceQuery(workspace_id=ws, page_size=10_000)


# ---- e2e: deploy + events (S271, retro covers S261/S265/S266) -------------


@pytest.mark.asyncio
async def test_deploy_e2e_with_events_and_canary() -> None:
    workspace_id = uuid4()
    agent_id = uuid4()
    artifact = DeployArtifact(
        id=uuid4(),
        workspace_id=workspace_id,
        agent_id=agent_id,
        version="v1",
        source_digest="abcdef0123456789",
    )
    builder = InMemoryImageBuilder()
    registry = InMemoryImageRegistry()
    kube = InMemoryKubeClient()
    eval_gate = InMemoryEvalGate(pass_rates=[0.95])
    baselines = InMemoryBaselineRegistry()

    controller = DeployController(
        builder=builder,
        registry=registry,
        kube=kube,
        eval_gate=eval_gate,
        baselines=baselines,
    )
    deploy = await controller.submit(artifact)

    # Hook the controller's lifecycle to a DeployEventStream.
    sink = InMemoryDeployEventSink()
    stream = DeployEventStream(sink, batch_size=4)
    await stream.emit(
        deploy_to_event(
            workspace_id=workspace_id,
            deploy_id=deploy.id,
            agent_id=agent_id,
            kind=DeployEventKind.SUBMITTED,
            at=_now(),
            to_stage=DeployPhase.PENDING.value,
        )
    )
    final = await controller.run(deploy.id)
    assert final.phase is DeployPhase.READY
    assert final.image_ref is not None
    await stream.emit(
        deploy_to_event(
            workspace_id=workspace_id,
            deploy_id=deploy.id,
            agent_id=agent_id,
            kind=DeployEventKind.PHASE_CHANGED,
            at=_now(),
            to_stage=DeployPhase.READY.value,
            extras={"image_ref": final.image_ref, "pass_rate": 0.95},
        )
    )

    # Now drive a canary FSM through full promotion and surface events.
    fsm = CanaryFSM(policy=CanaryPolicy(min_samples=1))
    decisions: list[CanaryDecision] = []
    for _ in range(3):
        decisions.append(fsm.step(_good(), now=_now()))
    assert decisions[-1].stage is CanaryStage.PROMOTED
    await stream.emit(
        deploy_to_event(
            workspace_id=workspace_id,
            deploy_id=deploy.id,
            agent_id=agent_id,
            kind=DeployEventKind.CANARY_PROMOTED,
            at=_now(),
            from_stage=CanaryStage.CANARY_50.value,
            to_stage=CanaryStage.PROMOTED.value,
        )
    )
    await stream.aclose()

    rows = sink.filter(workspace_id=workspace_id, deploy_id=deploy.id)
    kinds = [r.kind for r in rows]
    assert DeployEventKind.SUBMITTED in kinds
    assert DeployEventKind.PHASE_CHANGED in kinds
    assert DeployEventKind.CANARY_PROMOTED in kinds
    # Baseline was recorded after READY.
    rec = await baselines.get(workspace_id=workspace_id, agent_id=agent_id)
    assert rec == 0.95
