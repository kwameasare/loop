"""Tests for voice pass7: turn_take FSM, VAD/barge-in, voice cost."""

from __future__ import annotations

from uuid import uuid4

import pytest
from loop_voice.turn_take import (
    IllegalTurnTakeTransition,
    TurnTakeEvent,
    TurnTakeFSM,
    TurnTakeState,
)
from loop_voice.vad import (
    BargeInDetector,
    BargeInEvent,
    VadConfig,
    VadDetector,
    VadState,
)
from loop_voice.voice_cost import VoiceCallCostAggregator, VoiceCostRates

# ----- turn_take FSM ---------------------------------------------------------


def test_fsm_normal_turn_lifecycle() -> None:
    fsm = TurnTakeFSM()
    assert fsm.transition(TurnTakeEvent.USER_STARTED_TALKING) is TurnTakeState.LISTENING
    assert fsm.transition(TurnTakeEvent.VAD_SILENCE) is TurnTakeState.THINKING
    assert fsm.transition(TurnTakeEvent.LLM_FIRST_TOKEN) is TurnTakeState.SPEAKING
    assert fsm.is_speaking
    assert fsm.transition(TurnTakeEvent.TTS_COMPLETE) is TurnTakeState.IDLE


def test_fsm_barge_in_from_speaking() -> None:
    fsm = TurnTakeFSM(state=TurnTakeState.SPEAKING)
    assert fsm.transition(TurnTakeEvent.BARGE_IN) is TurnTakeState.LISTENING


def test_fsm_illegal_transition_raises() -> None:
    fsm = TurnTakeFSM()
    with pytest.raises(IllegalTurnTakeTransition):
        fsm.transition(TurnTakeEvent.LLM_FIRST_TOKEN)


def test_fsm_history_records_transitions() -> None:
    fsm = TurnTakeFSM()
    fsm.transition(TurnTakeEvent.USER_STARTED_TALKING)
    fsm.transition(TurnTakeEvent.VAD_SILENCE)
    assert len(fsm.history) == 2
    assert fsm.history[-1][2] is TurnTakeState.THINKING


def test_fsm_legal_events_introspection() -> None:
    legal = TurnTakeFSM.legal_events(TurnTakeState.SPEAKING)
    assert TurnTakeEvent.BARGE_IN in legal
    assert TurnTakeEvent.LLM_FIRST_TOKEN not in legal


# ----- VAD -------------------------------------------------------------------


def test_vad_onset_after_threshold_frames() -> None:
    vad = VadDetector(config=VadConfig(onset_db=-30, release_db=-50, onset_frames=3, release_frames=3))
    # below threshold — no transition
    assert vad.feed(-50.0) is None
    assert vad.feed(-50.0) is None
    # 3 frames above
    assert vad.feed(-20.0) is None
    assert vad.feed(-20.0) is None
    ev = vad.feed(-20.0)
    assert ev is BargeInEvent.SPEECH_ONSET
    assert vad.state is VadState.SPEAKING


def test_vad_release_after_silence() -> None:
    vad = VadDetector(config=VadConfig(onset_db=-30, release_db=-50, onset_frames=1, release_frames=2))
    vad.feed(-10.0)
    assert vad.state is VadState.SPEAKING
    vad.feed(-60.0)
    ev = vad.feed(-60.0)
    assert ev is BargeInEvent.SPEECH_RELEASE
    assert vad.state is VadState.SILENT


def test_vad_hysteresis_prevents_flap() -> None:
    vad = VadDetector(config=VadConfig(onset_db=-30, release_db=-50, onset_frames=2, release_frames=2))
    # frames in the gap (-30 < x < -50 inverted: between -50 and -30) should not flap
    vad.feed(-10)
    vad.feed(-10)
    assert vad.state is VadState.SPEAKING
    # mid-band frames keep speaking and reset below counter
    assert vad.feed(-40.0) is None
    assert vad.state is VadState.SPEAKING


def test_vad_config_validation() -> None:
    with pytest.raises(ValueError):
        VadConfig(onset_db=-50, release_db=-30)  # inverted
    with pytest.raises(ValueError):
        VadConfig(onset_frames=0)


def test_barge_in_detector_cuts_tts() -> None:
    fsm = TurnTakeFSM(state=TurnTakeState.SPEAKING)
    bi = BargeInDetector(
        vad=VadDetector(config=VadConfig(onset_db=-30, release_db=-50, onset_frames=1, release_frames=2)),
        fsm=fsm,
    )
    ev = bi.feed(-10.0)
    assert ev is BargeInEvent.BARGE_IN
    assert fsm.state is TurnTakeState.LISTENING
    assert bi.barge_ins == 1


def test_barge_in_idle_starts_listen() -> None:
    fsm = TurnTakeFSM()
    bi = BargeInDetector(
        vad=VadDetector(config=VadConfig(onset_db=-30, release_db=-50, onset_frames=1, release_frames=2)),
        fsm=fsm,
    )
    bi.feed(-10.0)
    assert fsm.state is TurnTakeState.LISTENING


# ----- voice_cost ------------------------------------------------------------


def test_voice_cost_rollup() -> None:
    agg = VoiceCallCostAggregator(workspace_id=uuid4(), call_id=uuid4())
    agg.add_asr(60.0)  # 1 min
    agg.add_tts(30.0)  # 0.5 min
    agg.add_carrier(60.0)
    agg.add_llm_tokens(tokens_in=2000, tokens_out=1000)
    ev = agg.finalize()
    rates = VoiceCostRates()
    expected = (
        rates.asr_per_minute_micro
        + rates.tts_per_minute_micro // 2
        + rates.carrier_per_minute_micro
        + 2 * rates.llm_in_per_1k_tokens_micro
        + 1 * rates.llm_out_per_1k_tokens_micro
    )
    assert ev.cost_usd_micro == expected


def test_voice_cost_rejects_negative() -> None:
    agg = VoiceCallCostAggregator(workspace_id=uuid4(), call_id=uuid4())
    with pytest.raises(ValueError):
        agg.add_asr(-1.0)
    with pytest.raises(ValueError):
        agg.add_llm_tokens(tokens_in=-1, tokens_out=0)


def test_voice_cost_total_aggregates() -> None:
    ev1 = VoiceCallCostAggregator(workspace_id=uuid4(), call_id=uuid4()).finalize()
    agg = VoiceCallCostAggregator(workspace_id=uuid4(), call_id=uuid4())
    agg.add_asr(60.0)
    ev2 = agg.finalize()
    assert VoiceCallCostAggregator.total_cost_micro([ev1, ev2]) == ev2.cost_usd_micro
