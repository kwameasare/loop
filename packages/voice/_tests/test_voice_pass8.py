"""Tests for voice pass8: pipeline_tracing (S370) + provider_failover (S389)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from loop_voice.pipeline_tracing import (
    InMemoryStageRecorder,
    StageKind,
    VoicePipelineTracer,
)
from loop_voice.provider_failover import (
    ProviderEntry,
    ProviderFailover,
    ProviderFailoverExhausted,
    ProviderState,
)

# ---- pipeline tracing (S370) ------------------------------------------------


class _FakeClock:
    def __init__(self) -> None:
        self.t = 0

    def __call__(self) -> int:
        self.t += 100
        return self.t


def test_pipeline_tracer_records_three_stages() -> None:
    rec = InMemoryStageRecorder()
    tracer = VoicePipelineTracer(
        workspace_id=uuid4(),
        call_id=uuid4(),
        turn_id=uuid4(),
        recorder=rec,
        clock_ms=_FakeClock(),
    )
    with tracer.stage(StageKind.ASR, provider="deepgram", model="nova-3") as s:
        s.audio_ms = 1500
        s.first_byte_ms = 80
    with tracer.stage(StageKind.LLM, provider="openai", model="gpt-5"):
        pass
    with tracer.stage(StageKind.TTS, provider="elevenlabs"):
        pass
    spans = rec.spans
    assert [s.kind for s in spans] == [StageKind.ASR, StageKind.LLM, StageKind.TTS]
    assert spans[0].audio_ms == 1500
    assert spans[0].duration_ms == 100  # one clock tick = 100ms
    trace = tracer.finalise()
    assert len(trace.spans) == 3


def test_pipeline_tracer_records_error_on_exception() -> None:
    rec = InMemoryStageRecorder()
    tracer = VoicePipelineTracer(
        workspace_id=uuid4(),
        call_id=uuid4(),
        turn_id=uuid4(),
        recorder=rec,
        clock_ms=_FakeClock(),
    )
    with pytest.raises(RuntimeError), tracer.stage(StageKind.ASR, provider="deepgram"):
        raise RuntimeError("connect failed")
    assert rec.spans[0].error is not None
    assert "RuntimeError" in rec.spans[0].error


def test_otel_attrs_projection() -> None:
    rec = InMemoryStageRecorder()
    tracer = VoicePipelineTracer(
        workspace_id=uuid4(),
        call_id=uuid4(),
        turn_id=uuid4(),
        recorder=rec,
        clock_ms=_FakeClock(),
    )
    with tracer.stage(StageKind.LLM, provider="openai", model="gpt-5") as s:
        s.first_byte_ms = 250
    attrs = rec.spans[0].to_otel_attrs()
    assert attrs["loop.voice.stage"] == "llm"
    assert attrs["loop.voice.provider"] == "openai"
    assert attrs["loop.voice.model"] == "gpt-5"
    assert attrs["loop.voice.first_byte_ms"] == 250


def test_voice_turn_trace_end_to_end() -> None:
    rec = InMemoryStageRecorder()
    clock = _FakeClock()
    tracer = VoicePipelineTracer(
        workspace_id=uuid4(),
        call_id=uuid4(),
        turn_id=uuid4(),
        recorder=rec,
        clock_ms=clock,
    )
    with tracer.stage(StageKind.ASR, provider="dg"):
        pass
    with tracer.stage(StageKind.LLM, provider="oai"):
        pass
    trace = tracer.finalise()
    # spans cover ticks 100..400 by clock; e2e is max-end - min-start
    assert trace.end_to_end_ms() == trace.spans[-1].ended_at_ms - trace.spans[0].started_at_ms


# ---- provider failover (S389) -----------------------------------------------


class _Now:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


@pytest.mark.asyncio
async def test_failover_uses_primary_when_healthy() -> None:
    calls: list[str] = []

    async def primary(text: str) -> str:
        calls.append("p")
        return f"P:{text}"

    async def secondary(text: str) -> str:
        calls.append("s")
        return f"S:{text}"

    fo = ProviderFailover(
        providers=[
            ProviderEntry(id="primary", call=primary),
            ProviderEntry(id="secondary", call=secondary),
        ]
    )
    now = _Now()
    out = await fo.call("hi", now_fn=now)
    assert out == "P:hi"
    assert calls == ["p"]


@pytest.mark.asyncio
async def test_failover_falls_through_after_threshold() -> None:
    async def primary(_: str) -> str:
        raise RuntimeError("provider-down")

    async def secondary(text: str) -> str:
        return f"S:{text}"

    fo = ProviderFailover(
        providers=[
            ProviderEntry(id="primary", call=primary),
            ProviderEntry(id="secondary", call=secondary),
        ],
        failure_threshold=3,
    )
    now = _Now()
    # First three calls: primary fails each time, secondary succeeds.
    for _ in range(3):
        out = await fo.call("x", now_fn=now)
        assert out == "S:x"
    # Primary should now be unhealthy.
    assert fo.state("primary", now=now()) is ProviderState.UNHEALTHY


@pytest.mark.asyncio
async def test_failover_exhaustion() -> None:
    async def boom(_: str) -> str:
        raise RuntimeError("dead")

    fo = ProviderFailover(
        providers=[
            ProviderEntry(id="a", call=boom),
            ProviderEntry(id="b", call=boom),
        ],
        failure_threshold=1,
    )
    now = _Now()
    # First call: a fails (threshold reached), b fails (threshold reached).
    with pytest.raises(ProviderFailoverExhausted) as exc:
        await fo.call("x", now_fn=now)
    assert "a" in exc.value.attempted
    assert "b" in exc.value.attempted
    assert isinstance(exc.value.last_error, RuntimeError)


@pytest.mark.asyncio
async def test_failover_cooldown_makes_provider_eligible_again() -> None:
    state = {"fail": True}

    async def flaky(_: str) -> str:
        if state["fail"]:
            raise RuntimeError("nope")
        return "ok"

    fo = ProviderFailover(
        providers=[ProviderEntry(id="only", call=flaky)],
        failure_threshold=1,
        cooldown_seconds=10.0,
    )
    now = _Now()
    with pytest.raises(ProviderFailoverExhausted):
        await fo.call("x", now_fn=now)
    # Right after failure: unhealthy.
    assert fo.state("only", now=now.t) is ProviderState.UNHEALTHY
    # After cooldown elapses: cooldown -> eligible.
    now.t += 11.0
    state["fail"] = False
    out = await fo.call("x", now_fn=now)
    assert out == "ok"


def test_failover_rejects_empty_provider_list() -> None:
    with pytest.raises(ValueError):
        ProviderFailover(providers=[])


def test_failover_rejects_duplicate_ids() -> None:
    async def f(_: str) -> str:
        return "x"

    with pytest.raises(ValueError):
        ProviderFailover(
            providers=[
                ProviderEntry(id="dup", call=f),
                ProviderEntry(id="dup", call=f),
            ]
        )
