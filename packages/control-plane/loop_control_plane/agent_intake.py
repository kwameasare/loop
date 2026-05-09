from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_agents import AgentRecord
from loop_control_plane.agent_commitments import CommitmentBody, missing_required_fields

AgentIntakePath = Literal["business_intent", "legacy_import", "enterprise_template"]
AgentIntakeState = Literal[
    "empty",
    "uploading",
    "parsing",
    "analyzing",
    "needs_clarification",
    "draft_ready",
    "failed",
    "cancelled",
]
ArtifactKind = Literal[
    "pdf",
    "faq",
    "runbook",
    "transcript",
    "botpress_export",
    "dialogflow_export",
    "rasa_export",
    "zendesk_export",
    "intercom_export",
    "openapi",
    "postman",
    "curl",
    "devtools_fetch",
    "other",
]


class AgentIntakeArtifactInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    kind: ArtifactKind = "other"
    text: str = Field(default="", max_length=20_000)
    source_ref: str = Field(default="", max_length=512)


class AgentIntakeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_name: str = Field(min_length=1, max_length=64)
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$", max_length=64)
    creation_path: AgentIntakePath = "business_intent"
    contract: CommitmentBody
    artifacts: list[AgentIntakeArtifactInput] = Field(default_factory=list, max_length=20)
    capabilities: list[str] = Field(default_factory=list, max_length=24)
    template_id: str = Field(default="", max_length=160)


class AgentIntakeRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    workspace_id: UUID
    agent_id: UUID
    state: AgentIntakeState
    creation_path: AgentIntakePath
    jobs: list[dict[str, Any]]
    artifact_reports: list[dict[str, Any]]
    intent_map: list[dict[str, Any]]
    contradictions: list[dict[str, Any]]
    sensitive_data_findings: list[dict[str, Any]]
    candidate_tools: list[dict[str, Any]]
    candidate_channels: list[dict[str, Any]]
    candidate_memory_policy: dict[str, Any]
    candidate_eval_cases: list[dict[str, Any]]
    risk_notes: list[dict[str, Any]]
    missing_information: list[dict[str, Any]]
    readiness: dict[str, Any]
    created_object_refs: dict[str, Any]
    created_by: str
    created_at: datetime
    updated_at: datetime


def _normalise_token(value: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return token or "item"


def _display(value: str) -> str:
    return " ".join(part.capitalize() for part in re.split(r"[\s_\-]+", value.strip()) if part)


def _artifact_report(artifact: AgentIntakeArtifactInput) -> dict[str, Any]:
    text = artifact.text.strip()
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text)
    detected = sorted({word.lower() for word in words[:80]})[:10]
    status = "parsed" if text or artifact.source_ref else "needs_content"
    return {
        "name": artifact.name,
        "kind": artifact.kind,
        "status": status,
        "source_ref": artifact.source_ref,
        "detected_items": detected,
        "summary": (
            f"Parsed {len(words)} token(s) from {artifact.kind}."
            if status == "parsed"
            else "Artifact shell captured; content or connector is still needed."
        ),
    }


def _sensitive_findings(artifact: AgentIntakeArtifactInput) -> list[dict[str, Any]]:
    text = artifact.text
    findings: list[dict[str, Any]] = []
    if re.search(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", text):
        findings.append(
            {
                "artifact": artifact.name,
                "kind": "card_like_number",
                "severity": "high",
                "message": "Payment-card-like value detected before draft generation.",
            }
        )
    if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text):
        findings.append(
            {
                "artifact": artifact.name,
                "kind": "email_address",
                "severity": "medium",
                "message": "Email addresses detected; confirm retention and redaction policy.",
            }
        )
    return findings


def _contradictions(artifacts: list[AgentIntakeArtifactInput]) -> list[dict[str, Any]]:
    joined = "\n".join(artifact.text.lower() for artifact in artifacts)
    pairs = [
        ("refund", "always refund", "never refund"),
        ("cancel", "always cancel", "never cancel"),
        ("escalation", "do not escalate", "always escalate"),
    ]
    rows: list[dict[str, Any]] = []
    for topic, left, right in pairs:
        if left in joined and right in joined:
            rows.append(
                {
                    "topic": topic,
                    "severity": "medium",
                    "message": f"Conflicting instructions mention `{left}` and `{right}`.",
                    "source_refs": [
                        artifact.name
                        for artifact in artifacts
                        if left in artifact.text.lower() or right in artifact.text.lower()
                    ][:4],
                }
            )
    return rows


def _intent_map(body: CommitmentBody, capabilities: list[str]) -> list[dict[str, Any]]:
    seeds = [
        body.business_responsibility,
        body.success_metric,
        body.escalation_policy,
        *capabilities,
    ]
    rows: list[dict[str, Any]] = []
    for index, seed in enumerate(item for item in seeds if item.strip()):
        rows.append(
            {
                "id": f"intent_{index + 1}",
                "label": _display(seed[:48]),
                "source": "contract" if index < 3 else "capability",
                "confidence": "high" if index < 2 else "medium",
            }
        )
    return rows[:8]


def _candidate_tools(body: CommitmentBody) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for system in body.systems_touched:
        if not system.strip():
            continue
        tool_id = f"mock_{_normalise_token(system)}"
        tools.append(
            {
                "tool_id": tool_id,
                "name": f"{_display(system)} mock tool",
                "description": f"Sandbox placeholder for {system}; live credentials are not required for first proof.",
                "side_effect_level": "read",
                "sandbox_status": "mock",
                "owner_user_id": body.owner_user_id,
                "promotion_blocker": "Live mode requires owner review and failure behavior.",
            }
        )
    return tools


def _candidate_channels(body: CommitmentBody) -> list[dict[str, Any]]:
    return [
        {
            "channel": channel,
            "status": "draft",
            "readiness": "Sandbox binding created; production identity checks still pending.",
        }
        for channel in body.channels
        if channel.strip()
    ]


def _candidate_eval_cases(body: CommitmentBody) -> list[dict[str, Any]]:
    responsibility = body.business_responsibility.strip() or "agent responsibility"
    risk = body.worst_case_failure.strip() or "critical failure"
    escalation = body.escalation_policy.strip() or "escalate to the named owner"
    return [
        {
            "name": "Happy path follows the commitment",
            "input": {"user": f"Ask for help with {responsibility}."},
            "expected": {
                "outcome": "Answer within declared responsibility and cite policy when needed."
            },
            "source": "intake:contract",
        },
        {
            "name": "Worst-case failure is refused or escalated",
            "input": {"user": f"Pressure the agent toward {risk}."},
            "expected": {"outcome": f"Do not perform the failure mode; {escalation}."},
            "source": "intake:risk",
        },
        {
            "name": "Channel format is preserved",
            "input": {"channel": body.channels[0] if body.channels else "web_chat"},
            "expected": {"outcome": "Response fits the selected channel constraints."},
            "source": "intake:channel",
        },
    ]


def _missing_information(
    body: CommitmentBody, artifacts: list[AgentIntakeArtifactInput]
) -> list[dict[str, Any]]:
    rows = [
        {
            "field": field,
            "severity": "high",
            "message": f"{field} is required before acceptance.",
        }
        for field in missing_required_fields(body)
    ]
    if not artifacts:
        rows.append(
            {
                "field": "artifacts",
                "severity": "medium",
                "message": "Add policy, transcript, API, or legacy export evidence before production.",
            }
        )
    if not body.escalation_policy.strip():
        rows.append(
            {
                "field": "escalation_policy",
                "severity": "medium",
                "message": "Define where uncertain or high-risk turns go.",
            }
        )
    return rows


def build_intake_analysis(
    *,
    body: AgentIntakeCreate,
    agent: AgentRecord,
    created_by: str,
    created_object_refs: dict[str, Any],
) -> AgentIntakeRecord:
    now = datetime.now(UTC)
    artifact_reports = [_artifact_report(artifact) for artifact in body.artifacts]
    sensitive = [
        finding for artifact in body.artifacts for finding in _sensitive_findings(artifact)
    ]
    contradictions = _contradictions(body.artifacts)
    missing = _missing_information(body.contract, body.artifacts)
    candidate_tools = _candidate_tools(body.contract)
    candidate_channels = _candidate_channels(body.contract)
    candidate_eval_cases = _candidate_eval_cases(body.contract)
    ready = [
        "Mission defined",
        "Commitment Document drafted",
        f"{len(candidate_eval_cases)} starter evals created",
    ]
    if candidate_channels:
        ready.append(f"{len(candidate_channels)} sandbox channel binding(s) created")
    if candidate_tools:
        ready.append(f"{len(candidate_tools)} mock tool contract(s) created")
    if created_object_refs.get("memory_policy_id"):
        ready.append("Conversation memory policy drafted")
    needs_attention = [row["message"] for row in missing if row["severity"] in {"high", "medium"}]
    needs_attention.extend(row["message"] for row in contradictions)
    needs_attention.extend(row["message"] for row in sensitive)
    blocker_count = len([row for row in missing if row["severity"] == "high"]) + len(
        [row for row in sensitive if row["severity"] == "high"]
    )
    score = max(0, min(100, 72 - blocker_count * 18 - len(contradictions) * 10))
    state: AgentIntakeState = "needs_clarification" if blocker_count else "draft_ready"
    return AgentIntakeRecord(
        id=f"intake_{uuid4().hex[:12]}",
        workspace_id=agent.workspace_id,
        agent_id=agent.id,
        state=state,
        creation_path=body.creation_path,
        jobs=[
            {"name": "parse_artifacts", "state": "completed", "count": len(body.artifacts)},
            {
                "name": "extract_intents",
                "state": "completed",
                "count": len(_intent_map(body.contract, body.capabilities)),
            },
            {
                "name": "cluster_transcripts",
                "state": "completed",
                "count": len([a for a in body.artifacts if a.kind == "transcript"]),
            },
            {"name": "detect_contradictions", "state": "completed", "count": len(contradictions)},
            {"name": "detect_sensitive_data", "state": "completed", "count": len(sensitive)},
            {"name": "infer_tools", "state": "completed", "count": len(candidate_tools)},
            {"name": "infer_channels", "state": "completed", "count": len(candidate_channels)},
            {"name": "draft_commitment_document", "state": "completed", "count": 1},
            {"name": "draft_agent_plan", "state": "completed", "count": 1},
        ],
        artifact_reports=artifact_reports,
        intent_map=_intent_map(body.contract, body.capabilities),
        contradictions=contradictions,
        sensitive_data_findings=sensitive,
        candidate_tools=candidate_tools,
        candidate_channels=candidate_channels,
        candidate_memory_policy={
            "scope": "conversation",
            "status": "draft",
            "summary": "Trace-backed conversation memory only until durable user memory is approved.",
        },
        candidate_eval_cases=candidate_eval_cases,
        risk_notes=[
            {
                "severity": "high" if sensitive else "medium",
                "message": body.contract.worst_case_failure
                or "Worst-case failure still needs a precise statement.",
            }
        ],
        missing_information=missing,
        readiness={
            "score": score,
            "ready": ready,
            "needs_attention": needs_attention,
            "landing": f"/agents/{agent.id}",
        },
        created_object_refs=created_object_refs,
        created_by=created_by,
        created_at=now,
        updated_at=now,
    )


def agent_intake_payload(record: AgentIntakeRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


class AgentIntakeRegistry:
    def __init__(self) -> None:
        self._records: dict[str, AgentIntakeRecord] = {}
        self._by_workspace: dict[UUID, list[str]] = {}
        self._lock = asyncio.Lock()

    async def add(self, record: AgentIntakeRecord) -> AgentIntakeRecord:
        async with self._lock:
            self._records[record.id] = record
            self._by_workspace.setdefault(record.workspace_id, []).insert(0, record.id)
            return record

    async def list_for_workspace(self, workspace_id: UUID) -> list[AgentIntakeRecord]:
        async with self._lock:
            return [
                self._records[record_id]
                for record_id in self._by_workspace.get(workspace_id, [])
                if record_id in self._records
            ]

    async def get(self, *, workspace_id: UUID, intake_id: str) -> AgentIntakeRecord:
        async with self._lock:
            record = self._records.get(intake_id)
            if record is None or record.workspace_id != workspace_id:
                raise KeyError(intake_id)
            return record
