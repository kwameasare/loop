"""Pass14 replay tests for S480-S487."""

from __future__ import annotations

import pytest
from loop_eval import (
    CassetteEntry,
    DeterministicTurnReplayer,
    InMemoryFrameLog,
    RecordedTurn,
    TurnFrame,
    TurnFrameRecorder,
    cassette_entry_to_sample,
    diff_recordings,
    load_recorded_turn,
    regression_case_for_turn,
    sample_to_eval_case_yaml,
    serialise_frame,
    turn_subject,
)


def _frame(
    seq: int,
    *,
    text: str,
    cost_usd: float = 0.0,
    latency_ms: float = 0.0,
) -> TurnFrame:
    return TurnFrame(
        turn_id="turn_123",
        seq=seq,
        kind="turn_event",
        timestamp_ms=1_700_000_000_000 + seq,
        payload={"text": text},
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )


@pytest.mark.asyncio
async def test_frame_recorder_writes_jsonl_to_turn_subject() -> None:
    sink = InMemoryFrameLog()
    subject = turn_subject("turn_123")
    recorder = TurnFrameRecorder(sink, subject=subject)
    await recorder.record_many([_frame(1, text="second"), _frame(0, text="first")])

    lines = await sink.read(subject)
    assert len(lines) == 2
    assert lines[0] == serialise_frame(_frame(1, text="second"))

    loaded = await load_recorded_turn(
        sink,
        subject=subject,
        turn_id="turn_123",
        version="v1",
    )
    assert [frame.seq for frame in loaded.frames] == [0, 1]
    assert loaded.frames[0].payload["text"] == "first"


@pytest.mark.asyncio
async def test_capture_then_replay_same_version_is_byte_equal() -> None:
    sink = InMemoryFrameLog()
    subject = turn_subject("turn_123")
    frames = (
        _frame(0, text="user: hi"),
        _frame(1, text="agent: hello", cost_usd=0.001, latency_ms=12.0),
    )
    await TurnFrameRecorder(sink, subject=subject).record_many(frames)

    recording = await load_recorded_turn(
        sink,
        subject=subject,
        turn_id="turn_123",
        version="v1",
    )
    replay = await DeterministicTurnReplayer().replay(recording, target_version="v1")
    result = diff_recordings(recording, replay)

    assert result.byte_equal is True
    assert result.diffs == ()
    assert result.passed is True


@pytest.mark.asyncio
async def test_replay_against_alternate_version_yields_diffable_frames() -> None:
    recording = RecordedTurn(
        turn_id="turn_123",
        subject=turn_subject("turn_123"),
        frames=(_frame(0, text="agent: hello"),),
        version="v1",
    )

    def transform(frame: TurnFrame) -> TurnFrame:
        return frame.model_copy(update={"payload": {"text": "agent: hi"}})

    replay = await DeterministicTurnReplayer().replay(
        recording,
        target_version="v2",
        transform=transform,
    )
    result = diff_recordings(recording, replay)

    assert result.byte_equal is False
    assert result.diffs[0].seq == 0
    assert "agent: hello" in (result.diffs[0].expected or "")
    assert "agent: hi" in (result.diffs[0].actual or "")


def test_diff_flags_cost_and_latency_regressions() -> None:
    expected = RecordedTurn(
        turn_id="turn_123",
        subject=turn_subject("turn_123"),
        frames=(_frame(0, text="ok", cost_usd=0.010, latency_ms=100.0),),
        version="v1",
    )
    actual = RecordedTurn(
        turn_id="turn_123",
        subject=turn_subject("turn_123"),
        frames=(_frame(0, text="ok", cost_usd=0.020, latency_ms=260.0),),
        version="v2",
    )

    result = diff_recordings(
        expected,
        actual,
        max_extra_cost_usd=0.001,
        max_extra_latency_ms=50.0,
    )

    assert result.cost_regressed is True
    assert result.latency_regressed is True
    assert result.cost_delta_usd == pytest.approx(0.010)
    assert result.latency_delta_ms == pytest.approx(160.0)


def test_cassette_entry_converts_to_eval_case_yaml() -> None:
    entry = CassetteEntry(
        request_key="abc123",
        request={"prompt": "Where is order 1234?", "model": "loop:smart"},
        response="Order 1234 shipped.",
        usage={"cost_usd": 0.002},
        recorded_at_ms=123,
    )

    sample = cassette_entry_to_sample(entry, sample_id="order-regression")
    yaml_text = sample_to_eval_case_yaml(sample, suite="regressions")

    assert sample.input == '{"model": "loop:smart", "prompt": "Where is order 1234?"}'
    assert sample.expected == "Order 1234 shipped."
    assert "order-regression" in yaml_text
    assert "cassette_request_key" in yaml_text


def test_prod_failure_builds_deploy_gate_regression_pr_payload() -> None:
    turn = RecordedTurn(
        turn_id="turn_123",
        subject=turn_subject("turn_123"),
        frames=(_frame(0, text="bad final answer"),),
        version="agent-v9",
        metadata={"workspace_id": "ws_1"},
    )

    pr = regression_case_for_turn(turn, sha="deadbeef")

    assert pr.path == "evals/regressions/deadbeef.yml"
    assert "turn_123" in pr.title
    assert "deploy-gate" in pr.yaml_text
    assert "bad final answer" in pr.yaml_text
