"""S824 memory-write PII redaction tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast
from uuid import uuid4

import pytest
from loop_runtime import MemoryPIIRedactor, MemoryScope, PIISpan, UserMemoryStore


@dataclass(frozen=True)
class _PresidioFinding:
    start: int
    end: int
    entity_type: str


class _FakePresidio:
    def analyze(
        self, *, text: str, entities: tuple[str, ...], language: str
    ) -> tuple[_PresidioFinding, ...]:
        assert "EMAIL_ADDRESS" in entities
        assert language == "en"
        start = text.index("patient-42")
        return (_PresidioFinding(start, start + len("patient-42"), "PATIENT_ID"),)


class _FakeLLMClassifier:
    def classify_pii(self, text: str) -> tuple[PIISpan, ...]:
        start = text.index("vip-codename")
        return (PIISpan(start, start + len("vip-codename"), "LLM_PII"),)


def test_regex_mode_redacts_nested_memory_values() -> None:
    redactor = MemoryPIIRedactor()
    value = {
        "email": "ada@example.com",
        "notes": ["Call +1 415 555 1212", "card 4242 4242 4242 4242"],
    }

    redacted = redactor.redact(value, mode="regex")

    assert redacted == {
        "email": "[EMAIL_REDACTED]",
        "notes": ["Call [PHONE_REDACTED]", "card [PAYMENT_CARD_REDACTED]"],
    }


def test_presidio_mode_uses_presidio_compatible_analyzer() -> None:
    redactor = MemoryPIIRedactor(presidio_analyzer=_FakePresidio())

    redacted = redactor.redact("store patient-42 in memory", mode="presidio")

    assert redacted == "store [PATIENT_ID_REDACTED] in memory"


def test_llm_classifier_mode_uses_classifier_spans() -> None:
    redactor = MemoryPIIRedactor(llm_classifier=_FakeLLMClassifier())

    redacted = redactor.redact("remember vip-codename for next turn", mode="llm_classifier")

    assert redacted == "remember [LLM_PII_REDACTED] for next turn"


def test_user_memory_store_applies_redaction_per_agent_on_write() -> None:
    workspace_id = uuid4()
    redacted_agent = uuid4()
    raw_agent = uuid4()
    store = UserMemoryStore()
    store.configure_agent_redaction(redacted_agent, "regex")

    redacted_scope = MemoryScope(workspace_id=workspace_id, agent_id=redacted_agent, user_id="u-1")
    raw_scope = MemoryScope(workspace_id=workspace_id, agent_id=raw_agent, user_id="u-1")
    store.put(redacted_scope, "profile", "email ada@example.com")
    store.put(raw_scope, "profile", "email ada@example.com")

    assert store.get(redacted_scope, "profile") == "email [EMAIL_REDACTED]"
    assert store.get(raw_scope, "profile") == "email ada@example.com"


def test_user_memory_store_rejects_unknown_redaction_mode() -> None:
    store = UserMemoryStore()
    with pytest.raises(ValueError, match="unsupported"):
        store.configure_agent_redaction(uuid4(), cast(Any, "classify-everything"))
