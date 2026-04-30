"""Tests for pass10 KB modules: episodic_retrieve (S492) + episodic_ttl (S493)."""

from __future__ import annotations

import pytest
from loop_kb_engine.episodic import EPISODIC_PAYLOAD_KEYS
from loop_kb_engine.episodic_retrieve import (
    EpisodicCandidate,
    RetrievalError,
    RetrievalPolicy,
    normalise_similarity,
    recency_score,
    retrieve_for_turn,
    validate_payload,
)
from loop_kb_engine.episodic_ttl import (
    EpisodeAgeRecord,
    PruneResult,
    TtlError,
    TtlPolicy,
    effective_ttl_ms,
    execute_prune,
    plan_prune,
)

DAY_MS = 24 * 60 * 60 * 1000


# --------------------------- retrieval ---------------------------


def test_policy_weights_must_sum_to_one():
    with pytest.raises(RetrievalError):
        RetrievalPolicy(recency_weight=0.4, similarity_weight=0.4)


def test_policy_k_must_be_positive():
    with pytest.raises(RetrievalError):
        RetrievalPolicy(k=0)


def test_recency_score_at_now_is_one():
    s = recency_score(occurred_at_ms=1_000, now_ms=1_000, half_life_ms=60_000)
    assert s == pytest.approx(1.0)


def test_recency_score_half_life():
    s = recency_score(occurred_at_ms=0, now_ms=60_000, half_life_ms=60_000)
    assert s == pytest.approx(0.5)


def test_normalise_similarity_edges():
    assert normalise_similarity(-1.0) == 0.0
    assert normalise_similarity(1.0) == 1.0
    assert normalise_similarity(0.0) == 0.5
    assert normalise_similarity(2.0) == 1.0  # clamps


class FakeReader:
    def __init__(self, candidates):
        self.candidates = candidates
        self.calls = 0

    async def search(self, *, agent_id, query_vector, limit):
        self.calls += 1
        return list(self.candidates[:limit])


@pytest.mark.asyncio
async def test_retrieve_pure_similarity_ordering():
    cands = [
        EpisodicCandidate(point_id="a", similarity=0.1, occurred_at_ms=0, payload={}),
        EpisodicCandidate(point_id="b", similarity=0.9, occurred_at_ms=0, payload={}),
        EpisodicCandidate(point_id="c", similarity=0.5, occurred_at_ms=0, payload={}),
    ]
    reader = FakeReader(cands)
    policy = RetrievalPolicy(k=3, similarity_weight=1.0, recency_weight=0.0)
    out = await retrieve_for_turn(
        reader=reader, agent_id="ag", query_vector=[1.0], now_ms=0, policy=policy
    )
    assert [s.candidate.point_id for s in out] == ["b", "c", "a"]


@pytest.mark.asyncio
async def test_retrieve_pure_recency_ordering():
    cands = [
        EpisodicCandidate(point_id="old", similarity=0.9, occurred_at_ms=0, payload={}),
        EpisodicCandidate(point_id="mid", similarity=0.9, occurred_at_ms=DAY_MS, payload={}),
        EpisodicCandidate(point_id="new", similarity=0.9, occurred_at_ms=2 * DAY_MS, payload={}),
    ]
    reader = FakeReader(cands)
    policy = RetrievalPolicy(
        k=3, similarity_weight=0.0, recency_weight=1.0, half_life_ms=DAY_MS
    )
    out = await retrieve_for_turn(
        reader=reader, agent_id="ag", query_vector=[1.0], now_ms=2 * DAY_MS, policy=policy
    )
    assert [s.candidate.point_id for s in out] == ["new", "mid", "old"]


@pytest.mark.asyncio
async def test_retrieve_max_age_filter():
    cands = [
        EpisodicCandidate(point_id="old", similarity=0.9, occurred_at_ms=0, payload={}),
        EpisodicCandidate(point_id="new", similarity=0.5, occurred_at_ms=DAY_MS, payload={}),
    ]
    reader = FakeReader(cands)
    policy = RetrievalPolicy(
        k=2,
        similarity_weight=1.0,
        recency_weight=0.0,
        half_life_ms=DAY_MS,
        max_age_ms=DAY_MS // 2,
    )
    out = await retrieve_for_turn(
        reader=reader, agent_id="ag", query_vector=[1.0], now_ms=DAY_MS, policy=policy
    )
    assert [s.candidate.point_id for s in out] == ["new"]


@pytest.mark.asyncio
async def test_retrieve_rejects_empty_vector():
    reader = FakeReader([])
    with pytest.raises(RetrievalError):
        await retrieve_for_turn(
            reader=reader,
            agent_id="ag",
            query_vector=[],
            now_ms=0,
            policy=RetrievalPolicy(),
        )


def test_validate_payload_happy():
    payload = {k: "x" for k in EPISODIC_PAYLOAD_KEYS}
    validate_payload(payload)


def test_validate_payload_missing_key():
    payload = {k: "x" for k in EPISODIC_PAYLOAD_KEYS if k != "summary"}
    with pytest.raises(RetrievalError):
        validate_payload(payload)


# --------------------------- TTL ---------------------------


def test_ttl_policy_validators():
    with pytest.raises(TtlError):
        TtlPolicy(ttl_days=0)
    with pytest.raises(TtlError):
        TtlPolicy(salience_multiplier=0.5)
    with pytest.raises(TtlError):
        TtlPolicy(high_salience_threshold=1.5)


def test_episode_age_record_validates_salience():
    with pytest.raises(TtlError):
        EpisodeAgeRecord(point_id="p", occurred_at_ms=0, salience=2.0, soft_deleted=False)


def test_effective_ttl_high_salience_extends():
    policy = TtlPolicy(ttl_days=10, salience_multiplier=2.0, high_salience_threshold=0.5)
    base = 10 * DAY_MS
    assert effective_ttl_ms(0.1, policy) == base
    assert effective_ttl_ms(0.9, policy) == int(base * 2.0)


def test_plan_prune_classifies_correctly():
    policy = TtlPolicy(
        ttl_days=10,
        hard_delete_grace_days=5,
        soft_delete=True,
        salience_multiplier=1.0,
        high_salience_threshold=1.0,  # only salience==1.0 would extend
    )
    now = 100 * DAY_MS
    eps = [
        EpisodeAgeRecord(point_id="fresh", occurred_at_ms=now - 2 * DAY_MS, salience=0.1, soft_deleted=False),
        EpisodeAgeRecord(point_id="expired", occurred_at_ms=now - 20 * DAY_MS, salience=0.1, soft_deleted=False),
        EpisodeAgeRecord(point_id="grace", occurred_at_ms=now - 12 * DAY_MS, salience=0.1, soft_deleted=True),
        EpisodeAgeRecord(point_id="grace_done", occurred_at_ms=now - 30 * DAY_MS, salience=0.1, soft_deleted=True),
    ]
    plan = plan_prune(episodes=eps, now_ms=now, policy=policy)
    assert "fresh" in plan.kept
    assert "expired" in plan.soft_deleted
    assert "grace" in plan.kept
    assert "grace_done" in plan.hard_deleted


def test_plan_prune_hard_deletes_when_soft_off():
    policy = TtlPolicy(ttl_days=10, hard_delete_grace_days=5, soft_delete=False)
    now = 100 * DAY_MS
    eps = [
        EpisodeAgeRecord(point_id="x", occurred_at_ms=now - 20 * DAY_MS, salience=0.0, soft_deleted=False),
    ]
    plan = plan_prune(episodes=eps, now_ms=now, policy=policy)
    assert plan.hard_deleted == ("x",)
    assert plan.soft_deleted == ()


@pytest.mark.asyncio
async def test_execute_prune_calls_writer_correctly():
    soft_calls: list = []
    hard_calls: list = []

    class W:
        async def soft_delete(self, *, agent_id, point_ids):
            soft_calls.append((agent_id, list(point_ids)))

        async def hard_delete(self, *, agent_id, point_ids):
            hard_calls.append((agent_id, list(point_ids)))

    plan = PruneResult(soft_deleted=("a", "b"), hard_deleted=("c",), kept=("d",))
    await execute_prune(writer=W(), agent_id="ag", plan=plan)
    assert soft_calls == [("ag", ["a", "b"])]
    assert hard_calls == [("ag", ["c"])]


@pytest.mark.asyncio
async def test_execute_prune_no_op_if_empty():
    class W:
        async def soft_delete(self, *, agent_id, point_ids):
            raise AssertionError("should not be called")

        async def hard_delete(self, *, agent_id, point_ids):
            raise AssertionError("should not be called")

    await execute_prune(writer=W(), agent_id="ag", plan=PruneResult((), (), ("kept",)))
