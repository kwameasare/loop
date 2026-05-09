from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_agents import AgentRecord

TurnRating = Literal["good", "bad", "risky", "unclear"]


class SimulatorTurnRatingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: TurnRating
    prompt: str = Field(min_length=1, max_length=4096)
    final_answer: str = Field(default="", max_length=8192)
    channel: str = Field(default="web", max_length=80)
    trace_id: str = Field(default="", max_length=256)
    issue_annotation: str = Field(default="", max_length=2048)
    save_as_eval: bool = False
    cost_usd: float = Field(default=0, ge=0)
    latency_ms: int = Field(default=0, ge=0)


class SimulatorTurnRatingRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    workspace_id: UUID
    agent_id: UUID
    rating: TurnRating
    prompt: str
    final_answer: str
    channel: str
    trace_id: str
    issue_annotation: str
    candidate_artifact: dict[str, Any]
    eval_case_ref: dict[str, Any] | None
    cost_usd: float
    latency_ms: int
    created_by: str
    created_at: datetime


def candidate_artifact_for(body: SimulatorTurnRatingCreate) -> dict[str, Any]:
    base = {
        "source": "first_proof",
        "rating": body.rating,
        "trace_id": body.trace_id or "trace/not-captured",
        "prompt": body.prompt,
        "annotation": body.issue_annotation,
    }
    if body.rating == "good":
        return {
            **base,
            "kind": "positive_eval_or_few_shot",
            "title": "Preserve this behavior",
            "expected_outcome": body.final_answer or "Match this accepted response pattern.",
        }
    if body.rating == "bad":
        return {
            **base,
            "kind": "regression_eval_candidate",
            "title": "Prevent this failure from recurring",
            "expected_outcome": body.issue_annotation
            or "Change the behavior so the answer matches the agent contract.",
        }
    if body.rating == "risky":
        return {
            **base,
            "kind": "risk_rule_candidate",
            "title": "Add a risk rule or escalation",
            "expected_outcome": body.issue_annotation
            or "Escalate or refuse when the risk condition appears.",
        }
    return {
        **base,
        "kind": "clarification_note_candidate",
        "title": "Clarify this ambiguous behavior",
        "expected_outcome": body.issue_annotation or "Ask a clarifying question before acting.",
    }


def simulator_turn_rating_payload(record: SimulatorTurnRatingRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


class SimulatorFeedbackRegistry:
    def __init__(self) -> None:
        self._items: dict[UUID, list[SimulatorTurnRatingRecord]] = {}
        self._lock = asyncio.Lock()

    async def add(
        self,
        *,
        agent: AgentRecord,
        body: SimulatorTurnRatingCreate,
        candidate_artifact: dict[str, Any],
        eval_case_ref: dict[str, Any] | None,
        actor_sub: str,
    ) -> SimulatorTurnRatingRecord:
        async with self._lock:
            record = SimulatorTurnRatingRecord(
                id=f"simrate_{uuid4().hex[:12]}",
                workspace_id=agent.workspace_id,
                agent_id=agent.id,
                rating=body.rating,
                prompt=body.prompt,
                final_answer=body.final_answer,
                channel=body.channel,
                trace_id=body.trace_id,
                issue_annotation=body.issue_annotation,
                candidate_artifact=candidate_artifact,
                eval_case_ref=eval_case_ref,
                cost_usd=body.cost_usd,
                latency_ms=body.latency_ms,
                created_by=actor_sub,
                created_at=datetime.now(UTC),
            )
            self._items.setdefault(agent.id, []).insert(0, record)
            return record

    async def list_for_agent(self, *, agent: AgentRecord) -> list[SimulatorTurnRatingRecord]:
        async with self._lock:
            return list(self._items.get(agent.id, []))
