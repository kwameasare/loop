"""S823 per-user memory isolation red-team tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from loop_runtime import MemoryScope, UserMemoryStore, run_user_memory_red_team


def test_user_memory_store_scopes_records_by_user_and_audits_without_values() -> None:
    workspace_id = uuid4()
    agent_id = uuid4()
    alice = MemoryScope(workspace_id=workspace_id, agent_id=agent_id, user_id="alice")
    bob = MemoryScope(workspace_id=workspace_id, agent_id=agent_id, user_id="bob")
    other_agent = MemoryScope(workspace_id=workspace_id, agent_id=uuid4(), user_id="alice")
    store = UserMemoryStore()

    store.put(alice, "profile", {"secret": "alice-only"})
    store.put(bob, "profile", {"secret": "bob-only"})

    assert store.get(alice, "profile") == {"secret": "alice-only"}
    assert store.get(bob, "profile") == {"secret": "bob-only"}
    assert store.get(other_agent, "profile") is None
    assert store.list_for_user(alice) == {"profile": {"secret": "alice-only"}}

    audit = store.audit_log()
    assert [event.action for event in audit] == ["put", "put", "get", "get", "get", "list"]
    assert audit[4].allowed is False
    assert "alice-only" not in repr(audit)
    assert "bob-only" not in repr(audit)


def test_user_memory_red_team_has_zero_leaks_and_false_positives_across_100k_cases() -> None:
    report = run_user_memory_red_team(cases=100_000)

    assert report.passed
    assert report.cases == 100_000
    assert report.leaks_detected == 0
    assert report.false_positives == 0
    assert report.audit_events == 300_000


def test_user_memory_store_rejects_ambiguous_scope_or_key() -> None:
    scope = MemoryScope(workspace_id=uuid4(), agent_id=uuid4(), user_id="u-1")
    store = UserMemoryStore()

    with pytest.raises(ValueError, match="user_id"):
        MemoryScope(workspace_id=uuid4(), agent_id=uuid4(), user_id="")
    with pytest.raises(ValueError, match="key"):
        store.put(scope, "", "value")
    with pytest.raises(ValueError, match="cases"):
        run_user_memory_red_team(cases=0)
