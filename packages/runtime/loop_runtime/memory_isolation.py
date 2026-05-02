"""Per-user memory isolation helpers for the runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from loop_runtime.memory_redaction import MemoryPIIRedactor, MemoryRedactionMode

__all__ = [
    "MemoryAuditEvent",
    "MemoryIsolationReport",
    "MemoryScope",
    "UserMemoryStore",
    "run_user_memory_red_team",
]


@dataclass(frozen=True)
class MemoryScope:
    workspace_id: UUID
    agent_id: UUID
    user_id: str

    def __post_init__(self) -> None:
        if not self.user_id:
            raise ValueError("user_id must be non-empty")


@dataclass(frozen=True)
class MemoryAuditEvent:
    action: str
    workspace_id: UUID
    agent_id: UUID
    user_id: str
    key: str
    allowed: bool


@dataclass(frozen=True)
class MemoryIsolationReport:
    cases: int
    leaks_detected: int
    false_positives: int
    audit_events: int

    @property
    def passed(self) -> bool:
        return self.leaks_detected == 0 and self.false_positives == 0


@dataclass
class UserMemoryStore:
    _records: dict[tuple[UUID, UUID, str, str], Any] = field(
        default_factory=dict[tuple[UUID, UUID, str, str], Any]
    )
    _audit: list[MemoryAuditEvent] = field(default_factory=list[MemoryAuditEvent])
    _redactor: MemoryPIIRedactor = field(default_factory=MemoryPIIRedactor)
    _redaction_by_agent: dict[UUID, MemoryRedactionMode] = field(
        default_factory=dict[UUID, MemoryRedactionMode]
    )

    def configure_agent_redaction(self, agent_id: UUID, mode: MemoryRedactionMode) -> None:
        if mode not in ("off", "regex", "presidio", "llm_classifier"):
            raise ValueError(f"unsupported memory redaction mode: {mode}")
        self._redaction_by_agent[agent_id] = mode

    def put(self, scope: MemoryScope, key: str, value: Any) -> None:
        self._validate_key(key)
        mode = self._redaction_by_agent.get(scope.agent_id, "off")
        self._records[self._entry(scope, key)] = self._redactor.redact(value, mode=mode)
        self._record("put", scope, key, allowed=True)

    def get(self, scope: MemoryScope, key: str) -> Any | None:
        self._validate_key(key)
        entry = self._entry(scope, key)
        allowed = entry in self._records
        self._record("get", scope, key, allowed=allowed)
        return self._records.get(entry)

    def list_for_user(self, scope: MemoryScope) -> dict[str, Any]:
        out = {
            key: value
            for (workspace_id, agent_id, user_id, key), value in self._records.items()
            if (
                workspace_id == scope.workspace_id
                and agent_id == scope.agent_id
                and user_id == scope.user_id
            )
        }
        self._record("list", scope, "*", allowed=True)
        return out

    def audit_log(self) -> tuple[MemoryAuditEvent, ...]:
        return tuple(self._audit)

    @staticmethod
    def _entry(scope: MemoryScope, key: str) -> tuple[UUID, UUID, str, str]:
        return (scope.workspace_id, scope.agent_id, scope.user_id, key)

    def _record(self, action: str, scope: MemoryScope, key: str, *, allowed: bool) -> None:
        self._audit.append(
            MemoryAuditEvent(
                action=action,
                workspace_id=scope.workspace_id,
                agent_id=scope.agent_id,
                user_id=scope.user_id,
                key=key,
                allowed=allowed,
            )
        )

    @staticmethod
    def _validate_key(key: str) -> None:
        if not key:
            raise ValueError("memory key must be non-empty")


def _stable_uuid(label: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"loop:memory-isolation:{label}")


def run_user_memory_red_team(*, cases: int = 100_000) -> MemoryIsolationReport:
    if cases < 1:
        raise ValueError("cases must be positive")
    store = UserMemoryStore()
    workspaces = tuple(_stable_uuid(f"workspace:{i}") for i in range(32))
    agents = tuple(_stable_uuid(f"agent:{i}") for i in range(8))
    leaks = 0
    false_positives = 0

    for index in range(cases):
        scope = MemoryScope(
            workspace_id=workspaces[index % len(workspaces)],
            agent_id=agents[index % len(agents)],
            user_id=f"user-{index % 4096}",
        )
        intruder = MemoryScope(
            workspace_id=scope.workspace_id,
            agent_id=scope.agent_id,
            user_id=f"intruder-{index % 4096}",
        )
        key = f"profile:{index % 97}"
        value = {"case": index, "marker": f"secret-{index}"}

        store.put(scope, key, value)
        if store.get(scope, key) != value:
            false_positives += 1
        if store.get(intruder, key) is not None:
            leaks += 1

    return MemoryIsolationReport(
        cases=cases,
        leaks_detected=leaks,
        false_positives=false_positives,
        audit_events=len(store.audit_log()),
    )
