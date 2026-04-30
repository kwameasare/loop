"""Deploy events stream → ClickHouse adapter (S269).

Every transition in :mod:`loop_control_plane.deploy` and
:mod:`loop_control_plane.canary` should emit a
:class:`DeployEvent` row to ClickHouse so the studio deploy tab can
render history and ops can build dashboards.

ClickHouse-the-driver is *not* a dependency. The adapter speaks to a
:class:`DeployEventSink` Protocol; production wires
``ClickHouseSink`` (in a sibling module that owns the http session)
and tests wire :class:`InMemoryDeployEventSink`.

The schema is fixed and matches ``deploy_events`` in
``loop_implementation/data/SCHEMA.md``::

    workspace_id  UUID
    deploy_id     UUID
    agent_id      UUID
    kind          LowCardinality(String)
    from_stage    LowCardinality(String)
    to_stage      LowCardinality(String)
    reason        String
    image_ref     Nullable(String)
    pass_rate     Nullable(Float32)
    at            DateTime64(3, 'UTC')
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "DeployEvent",
    "DeployEventKind",
    "DeployEventSink",
    "DeployEventStream",
    "InMemoryDeployEventSink",
    "deploy_to_event",
]


class DeployEventKind(StrEnum):
    SUBMITTED = "submitted"
    PHASE_CHANGED = "phase_changed"
    EVAL_RECORDED = "eval_recorded"
    CANARY_PROMOTED = "canary_promoted"
    CANARY_REGRESSION = "canary_regression"
    ROLLED_BACK = "rolled_back"


class DeployEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    workspace_id: UUID
    deploy_id: UUID
    agent_id: UUID
    kind: DeployEventKind
    from_stage: str = ""
    to_stage: str = ""
    reason: str = ""
    image_ref: str | None = None
    pass_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    at: datetime

    def to_row(self) -> dict[str, object]:
        """Project to the ClickHouse row layout (column-name keys)."""
        return {
            "workspace_id": str(self.workspace_id),
            "deploy_id": str(self.deploy_id),
            "agent_id": str(self.agent_id),
            "kind": self.kind.value,
            "from_stage": self.from_stage,
            "to_stage": self.to_stage,
            "reason": self.reason,
            "image_ref": self.image_ref,
            "pass_rate": self.pass_rate,
            "at": self.at.isoformat(),
        }


class DeployEventSink(Protocol):
    async def append(self, event: DeployEvent) -> None: ...
    async def append_many(self, events: list[DeployEvent]) -> None: ...


class InMemoryDeployEventSink:
    """Test fake; preserves insertion order, lock-free single-task usage."""

    def __init__(self) -> None:
        self.events: list[DeployEvent] = []

    async def append(self, event: DeployEvent) -> None:
        self.events.append(event)

    async def append_many(self, events: list[DeployEvent]) -> None:
        self.events.extend(events)

    def filter(
        self, *, workspace_id: UUID | None = None, deploy_id: UUID | None = None
    ) -> list[DeployEvent]:
        out = list(self.events)
        if workspace_id is not None:
            out = [e for e in out if e.workspace_id == workspace_id]
        if deploy_id is not None:
            out = [e for e in out if e.deploy_id == deploy_id]
        return out


class DeployEventStream:
    """Buffered façade around a :class:`DeployEventSink`.

    Buffers up to ``batch_size`` events before flushing so the
    ClickHouse insert is one round-trip per batch. Callers ``flush``
    explicitly at deploy boundaries; ``aclose`` flushes any tail.
    """

    def __init__(self, sink: DeployEventSink, *, batch_size: int = 32) -> None:
        if batch_size < 1:
            raise ValueError(f"batch_size must be >= 1, got {batch_size}")
        self._sink = sink
        self._batch_size = batch_size
        self._buffer: list[DeployEvent] = []

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)

    async def emit(self, event: DeployEvent) -> None:
        self._buffer.append(event)
        if len(self._buffer) >= self._batch_size:
            await self.flush()

    async def flush(self) -> None:
        if not self._buffer:
            return
        batch, self._buffer = self._buffer, []
        await self._sink.append_many(batch)

    async def aclose(self) -> None:
        await self.flush()


def deploy_to_event(
    *,
    workspace_id: UUID,
    deploy_id: UUID,
    agent_id: UUID,
    kind: DeployEventKind,
    at: datetime,
    from_stage: str = "",
    to_stage: str = "",
    reason: str = "",
    extras: Mapping[str, object] | None = None,
) -> DeployEvent:
    """Convenience builder used by the controller hook (S266)."""
    extras_map = extras or {}
    image_ref = extras_map.get("image_ref")
    pass_rate = extras_map.get("pass_rate")
    if image_ref is not None and not isinstance(image_ref, str):
        raise TypeError("extras['image_ref'] must be str")
    if pass_rate is not None and not isinstance(pass_rate, (int, float)):
        raise TypeError("extras['pass_rate'] must be number")
    return DeployEvent(
        workspace_id=workspace_id,
        deploy_id=deploy_id,
        agent_id=agent_id,
        kind=kind,
        from_stage=from_stage,
        to_stage=to_stage,
        reason=reason,
        image_ref=image_ref if isinstance(image_ref, str) else None,
        pass_rate=float(pass_rate) if isinstance(pass_rate, (int, float)) else None,
        at=at,
    )
