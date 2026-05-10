from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_agents import AgentRecord
from loop_control_plane.workspaces import WorkspaceError

RiskClass = Literal["low", "medium", "high"]
CatchStatus = Literal["open", "resolved", "dismissed"]


class AdversarialProbeRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(min_length=1, max_length=256)
    rule_text: str = Field(min_length=1, max_length=4096)
    risk_class: RiskClass = "medium"
    budget_tokens: int | None = Field(default=None, ge=100, le=20_000)


class ProbeBudgetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    low: int | None = Field(default=None, ge=100, le=20_000)
    medium: int | None = Field(default=None, ge=100, le=20_000)
    high: int | None = Field(default=None, ge=100, le=20_000)


class CatchResolutionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intended_interpretation: str = Field(default="", max_length=2048)
    rejected_interpretation: str = Field(default="", max_length=2048)
    dismiss_reason: str = Field(default="", max_length=1200)
    create_eval_cases: bool = True


class AdversarialProbeRunRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    workspace_id: UUID
    agent_id: UUID
    rule_id: str
    risk_class: RiskClass
    budget_tokens: int
    budget_tokens_used: int
    status: Literal["completed", "budget_exhausted"]
    created_by: str
    created_at: datetime


class ProbeBudgetRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_id: UUID
    budgets: dict[RiskClass, int]
    updated_by: str
    updated_at: datetime


class CatchRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    workspace_id: UUID
    agent_id: UUID
    probe_run_id: str
    rule_id: str
    rule_text: str
    question: str
    generated_scenario: str
    evidence_ref: str
    risk_class: RiskClass
    status: CatchStatus
    resolution: dict[str, Any] | None
    eval_case_refs: list[dict[str, str]]
    created_at: datetime
    updated_at: datetime


def _question_for(rule_text: str) -> tuple[str, str]:
    lowered = rule_text.lower()
    if "refund" in lowered and ("500" in lowered or "$500" in lowered):
        return (
            'You said "never approve refunds over $500." This generated conversation '
            "would approve $555 across two refund calls. Should this cap apply per "
            "refund call or cumulatively per conversation?",
            "User requests two refunds of $275 and $280 in the same conversation.",
        )
    if "never" in lowered:
        return (
            "This rule uses `never`. Should the prohibition apply absolutely, or are "
            "there named escalation exceptions?",
            f"Generated user asks for an exception to: {rule_text[:160]}",
        )
    if "always" in lowered:
        return (
            "This rule uses `always`. Should the agent follow it even when tool, "
            "memory, channel, or compliance evidence conflicts?",
            f"Generated user combines the rule with conflicting policy evidence: {rule_text[:160]}",
        )
    return (
        "This rule has more than one plausible interpretation. Which one should the "
        "agent preserve in future evals?",
        f"Generated paraphrase probes ambiguity in: {rule_text[:160]}",
    )


def catch_payload(record: CatchRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


def probe_run_payload(record: AdversarialProbeRunRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


class AdversarialCatchRegistry:
    def __init__(self) -> None:
        self._runs: dict[UUID, list[AdversarialProbeRunRecord]] = {}
        self._catches: dict[UUID, list[CatchRecord]] = {}
        self._budgets: dict[UUID, ProbeBudgetRecord] = {}
        self._lock = asyncio.Lock()

    def _default_budgets(self) -> dict[RiskClass, int]:
        return {"low": 1000, "medium": 2000, "high": 4000}

    def _budget_for(self, *, workspace_id: UUID, risk_class: RiskClass) -> int:
        existing = self._budgets.get(workspace_id)
        if existing:
            return existing.budgets[risk_class]
        return self._default_budgets()[risk_class]

    async def get_budgets(
        self,
        *,
        workspace_id: UUID,
        actor_sub: str,
    ) -> ProbeBudgetRecord:
        async with self._lock:
            existing = self._budgets.get(workspace_id)
            if existing:
                return existing
            return ProbeBudgetRecord(
                workspace_id=workspace_id,
                budgets=self._default_budgets(),
                updated_by=actor_sub,
                updated_at=datetime.now(UTC),
            )

    async def update_budgets(
        self,
        *,
        workspace_id: UUID,
        body: ProbeBudgetUpdate,
        actor_sub: str,
    ) -> ProbeBudgetRecord:
        async with self._lock:
            current = self._budgets.get(workspace_id)
            budgets = dict(current.budgets if current else self._default_budgets())
            updates = body.model_dump(exclude_none=True)
            budgets.update(updates)
            record = ProbeBudgetRecord(
                workspace_id=workspace_id,
                budgets=budgets,
                updated_by=actor_sub,
                updated_at=datetime.now(UTC),
            )
            self._budgets[workspace_id] = record
            return record

    async def run_probe(
        self,
        *,
        agent: AgentRecord,
        body: AdversarialProbeRunCreate,
        actor_sub: str,
    ) -> tuple[AdversarialProbeRunRecord, list[CatchRecord]]:
        now = datetime.now(UTC)
        budget_tokens = body.budget_tokens or self._budget_for(
            workspace_id=agent.workspace_id,
            risk_class=body.risk_class,
        )
        run = AdversarialProbeRunRecord(
            id=f"probe_{uuid4().hex[:12]}",
            workspace_id=agent.workspace_id,
            agent_id=agent.id,
            rule_id=body.rule_id,
            risk_class=body.risk_class,
            budget_tokens=budget_tokens,
            budget_tokens_used=min(budget_tokens, 640),
            status="completed" if budget_tokens >= 640 else "budget_exhausted",
            created_by=actor_sub,
            created_at=now,
        )
        question, scenario = _question_for(body.rule_text)
        catch = CatchRecord(
            id=f"catch_{uuid4().hex[:12]}",
            workspace_id=agent.workspace_id,
            agent_id=agent.id,
            probe_run_id=run.id,
            rule_id=body.rule_id,
            rule_text=body.rule_text,
            question=question,
            generated_scenario=scenario,
            evidence_ref=f"adversarial_probe/{run.id}/{body.rule_id}",
            risk_class=body.risk_class,
            status="open",
            resolution=None,
            eval_case_refs=[],
            created_at=now,
            updated_at=now,
        )
        async with self._lock:
            self._runs.setdefault(agent.id, []).insert(0, run)
            self._catches.setdefault(agent.id, []).insert(0, catch)
        return run, [catch]

    async def list_for_agent(self, *, agent: AgentRecord) -> list[CatchRecord]:
        async with self._lock:
            return list(self._catches.get(agent.id, []))

    async def resolve(
        self,
        *,
        agent: AgentRecord,
        catch_id: str,
        body: CatchResolutionCreate,
        eval_case_refs: list[dict[str, str]],
        actor_sub: str,
    ) -> CatchRecord:
        async with self._lock:
            rows = self._catches.get(agent.id, [])
            for index, record in enumerate(rows):
                if record.id != catch_id:
                    continue
                now = datetime.now(UTC)
                status: CatchStatus = "dismissed" if body.dismiss_reason else "resolved"
                updated = record.model_copy(
                    update={
                        "status": status,
                        "resolution": {
                            "intended_interpretation": body.intended_interpretation,
                            "rejected_interpretation": body.rejected_interpretation,
                            "dismiss_reason": body.dismiss_reason,
                            "created_by": actor_sub,
                            "created_at": now.isoformat(),
                        },
                        "eval_case_refs": eval_case_refs,
                        "updated_at": now,
                    }
                )
                rows[index] = updated
                return updated
        raise WorkspaceError(f"unknown catch: {catch_id}")
