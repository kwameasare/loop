from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from math import ceil
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_agents import AgentRecord
from loop_control_plane.tool_contracts import ToolContractRecord

ToolCallStatus = Literal["success", "error"]
ToolMetricStatus = Literal["measured", "waiting_for_calls"]


class ToolCallTelemetryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(min_length=1, max_length=160)
    latency_ms: int = Field(ge=0, le=300_000)
    status: ToolCallStatus = "success"
    retry_count: int = Field(default=0, ge=0, le=100)
    pii_sent: int = Field(default=0, ge=0, le=1000)
    schema_hash: str = Field(default="", max_length=160)
    cost_usd: float = Field(default=0, ge=0)
    occurred_at: datetime | None = None


class ToolCallTelemetryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    workspace_id: UUID
    agent_id: UUID
    tool_id: str
    trace_id: str
    latency_ms: int
    status: ToolCallStatus
    retry_count: int
    pii_sent: int
    schema_hash: str
    cost_usd: float
    occurred_at: datetime


class ToolContractMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_id: str
    production_usage_7d: int
    success_rate_percent: float
    p95_latency_ms: int
    retry_rate_percent: float
    failed_calls_7d: int
    pii_sent_7d: int
    last_schema_change_at: datetime | None
    measurement_status: ToolMetricStatus
    evidence_ref: str


@dataclass
class ToolCallTelemetryStore:
    _records: list[ToolCallTelemetryRecord] = field(default_factory=list)

    def record(
        self,
        *,
        agent: AgentRecord,
        tool_id: str,
        body: ToolCallTelemetryInput,
        now: datetime | None = None,
    ) -> ToolCallTelemetryRecord:
        occurred_at = body.occurred_at or now or datetime.now(UTC)
        record = ToolCallTelemetryRecord(
            id=f"tct_{uuid4().hex[:12]}",
            workspace_id=agent.workspace_id,
            agent_id=agent.id,
            tool_id=tool_id,
            trace_id=body.trace_id,
            latency_ms=body.latency_ms,
            status=body.status,
            retry_count=body.retry_count,
            pii_sent=body.pii_sent,
            schema_hash=body.schema_hash,
            cost_usd=body.cost_usd,
            occurred_at=occurred_at,
        )
        self._records.append(record)
        return record

    def list_for_agent(self, *, agent: AgentRecord) -> tuple[ToolCallTelemetryRecord, ...]:
        return tuple(
            record
            for record in self._records
            if record.workspace_id == agent.workspace_id and record.agent_id == agent.id
        )

    def metrics_for_agent(
        self,
        *,
        agent: AgentRecord,
        contracts: Sequence[ToolContractRecord],
        now: datetime | None = None,
    ) -> tuple[ToolContractMetrics, ...]:
        current = now or datetime.now(UTC)
        window_start = current - timedelta(days=7)
        records = [
            record
            for record in self.list_for_agent(agent=agent)
            if record.occurred_at >= window_start
        ]
        contract_by_tool = {contract.tool_id: contract for contract in contracts}
        tool_ids = sorted({*contract_by_tool.keys(), *(record.tool_id for record in records)})
        return tuple(
            _metrics_for_tool(
                tool_id=tool_id,
                records=[record for record in records if record.tool_id == tool_id],
                contract=contract_by_tool.get(tool_id),
            )
            for tool_id in tool_ids
        )


def _p95(values: Sequence[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, ceil(len(ordered) * 0.95) - 1)
    return ordered[index]


def _percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 1)


def _metrics_for_tool(
    *,
    tool_id: str,
    records: Sequence[ToolCallTelemetryRecord],
    contract: ToolContractRecord | None,
) -> ToolContractMetrics:
    total = len(records)
    failed = sum(1 for record in records if record.status == "error")
    retrying = sum(1 for record in records if record.retry_count > 0)
    pii_sent = sum(record.pii_sent for record in records)
    status: ToolMetricStatus = "measured" if total > 0 else "waiting_for_calls"
    schema_times = [record.occurred_at for record in records if record.schema_hash]
    last_schema_change_at = (
        max(schema_times) if schema_times else contract.updated_at if contract else None
    )
    evidence_ref = (
        f"tool-telemetry/{tool_id}/{total}-calls"
        if total > 0
        else f"tool-telemetry/{tool_id}/waiting-for-calls"
    )
    return ToolContractMetrics(
        tool_id=tool_id,
        production_usage_7d=total,
        success_rate_percent=_percent(total - failed, total),
        p95_latency_ms=_p95([record.latency_ms for record in records]),
        retry_rate_percent=_percent(retrying, total),
        failed_calls_7d=failed,
        pii_sent_7d=pii_sent,
        last_schema_change_at=last_schema_change_at,
        measurement_status=status,
        evidence_ref=evidence_ref,
    )
