"""Pass9 tests for control-plane: trial-conversion email nudges."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from loop_control_plane.billing_nudges import (
    TRIAL_LENGTH_DAYS,
    TrialNudgeKind,
    TrialNudgeScheduler,
    TrialState,
    utcnow,
)


def _ts(days: int) -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=days)


def test_seven_days_left_fires_at_day_7():
    ws = uuid4()
    trial = TrialState(workspace_id=ws, started_at=_ts(0))
    sch = TrialNudgeScheduler()
    out = sch.due(trials=[trial], now=_ts(7), already_sent=set())
    kinds = {n.kind for n in out}
    assert TrialNudgeKind.SEVEN_DAYS_LEFT in kinds
    assert TrialNudgeKind.ONE_DAY_LEFT not in kinds


def test_one_day_left_fires_at_day_13():
    ws = uuid4()
    trial = TrialState(workspace_id=ws, started_at=_ts(0))
    sch = TrialNudgeScheduler()
    out = sch.due(trials=[trial], now=_ts(13), already_sent=set())
    kinds = {n.kind for n in out}
    assert TrialNudgeKind.ONE_DAY_LEFT in kinds
    assert TrialNudgeKind.EXPIRED not in kinds


def test_expired_fires_at_day_14():
    ws = uuid4()
    trial = TrialState(workspace_id=ws, started_at=_ts(0))
    sch = TrialNudgeScheduler()
    out = sch.due(trials=[trial], now=_ts(14), already_sent=set())
    kinds = {n.kind for n in out}
    assert TrialNudgeKind.EXPIRED in kinds


def test_already_sent_is_not_resent():
    ws = uuid4()
    trial = TrialState(workspace_id=ws, started_at=_ts(0))
    sch = TrialNudgeScheduler()
    out = sch.due(
        trials=[trial],
        now=_ts(14),
        already_sent={(ws, TrialNudgeKind.SEVEN_DAYS_LEFT), (ws, TrialNudgeKind.ONE_DAY_LEFT)},
    )
    kinds = {n.kind for n in out}
    assert kinds == {TrialNudgeKind.EXPIRED}


def test_converted_trials_are_skipped():
    ws = uuid4()
    trial = TrialState(workspace_id=ws, started_at=_ts(0), converted=True)
    sch = TrialNudgeScheduler()
    assert sch.due(trials=[trial], now=_ts(14), already_sent=set()) == []


def test_opted_out_workspaces_skipped():
    ws = uuid4()
    trial = TrialState(workspace_id=ws, started_at=_ts(0))
    sch = TrialNudgeScheduler(opted_out={ws})
    assert sch.due(trials=[trial], now=_ts(14), already_sent=set()) == []


def test_naive_datetime_started_at_rejected():
    with pytest.raises(ValueError):
        TrialState(workspace_id=uuid4(), started_at=datetime(2026, 1, 1))


def test_naive_now_rejected():
    sch = TrialNudgeScheduler()
    with pytest.raises(ValueError):
        sch.due(trials=[], now=datetime(2026, 1, 1), already_sent=set())


def test_trial_length_constant():
    assert TRIAL_LENGTH_DAYS == 14


def test_results_sorted_deterministically():
    ws_a = uuid4()
    ws_b = uuid4()
    sch = TrialNudgeScheduler()
    trials = [
        TrialState(workspace_id=ws_a, started_at=_ts(0)),
        TrialState(workspace_id=ws_b, started_at=_ts(1)),  # offset by 1 day
    ]
    out = sch.due(trials=trials, now=_ts(20), already_sent=set())
    times = [n.scheduled_for for n in out]
    assert times == sorted(times)


def test_utcnow_returns_aware_datetime():
    assert utcnow().tzinfo is not None
