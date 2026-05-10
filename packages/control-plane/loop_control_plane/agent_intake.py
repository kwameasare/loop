from __future__ import annotations

import asyncio
import json
import re
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlparse
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
    candidate_knowledge_sources: list[dict[str, Any]]
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


ENTERPRISE_TEMPLATES: dict[str, dict[str, Any]] = {
    "tmpl_support_agent": {
        "name": "Enterprise support agent",
        "summary": "Policy-grounded web, WhatsApp, and email support.",
        "capabilities": [
            "Answer policy-backed support questions",
            "Escalate billing and legal risk",
            "Preserve channel formatting",
        ],
        "contract": {
            "business_responsibility": "Resolve support questions using approved policy and escalation paths.",
            "target_users": "Enterprise customers and support operators.",
            "worst_case_failure": "Promises refunds, legal positions, or account actions outside approved policy.",
            "channels": ["web", "whatsapp", "email"],
            "systems_touched": ["crm", "billing api"],
            "regions": ["us-east-1", "eu-west-2"],
            "languages": ["en"],
            "success_metric": "95% eval pass rate before canary.",
            "compliance_domain": "SOC2 support operations",
            "expected_volume": "10k turns per month",
            "budget_target": "$0.08 per resolved turn",
            "out_of_scope": "Legal advice and refunds above policy.",
            "escalation_policy": "Escalate policy conflicts, legal threats, and refund exceptions to the support lead.",
        },
        "artifacts": [
            {
                "name": "enterprise-support-template.md",
                "kind": "runbook",
                "text": "Use approved policy. Escalate legal threats. Never refund outside policy.",
                "source_ref": "template/tmpl_support_agent/runbook",
            }
        ],
    },
    "tmpl_voice_receptionist": {
        "name": "Voice receptionist",
        "summary": "Voice and SMS receptionist with handoff-safe routing.",
        "capabilities": [
            "Answer front-desk questions",
            "Schedule handoffs",
            "Collect callback context",
        ],
        "contract": {
            "business_responsibility": "Handle inbound calls, answer basic questions, and route callers to the right team.",
            "target_users": "Prospects, customers, and operators calling the business.",
            "worst_case_failure": "Books, cancels, or promises appointments without confirmation.",
            "channels": ["voice", "sms"],
            "systems_touched": ["calendar", "crm"],
            "regions": ["us-east-1"],
            "languages": ["en"],
            "success_metric": "90% successful route or callback capture.",
            "compliance_domain": "Customer communications",
            "expected_volume": "3k calls per month",
            "budget_target": "$0.12 per handled call",
            "out_of_scope": "Medical, legal, or financial advice.",
            "escalation_policy": "Escalate urgent, regulated, or frustrated callers to the human queue.",
        },
        "artifacts": [
            {
                "name": "voice-receptionist-template.md",
                "kind": "runbook",
                "text": "Confirm identity before scheduling. Keep speech concise. Escalate urgent callers.",
                "source_ref": "template/tmpl_voice_receptionist/runbook",
            }
        ],
    },
}


def template_payloads() -> list[dict[str, Any]]:
    return [
        {
            "id": template_id,
            "name": str(template["name"]),
            "summary": str(template["summary"]),
            "channels": list(template["contract"]["channels"]),
            "systems_touched": list(template["contract"]["systems_touched"]),
            "contract": dict(template["contract"]),
            "capabilities": list(template["capabilities"]),
            "artifacts": [dict(artifact) for artifact in template["artifacts"]],
        }
        for template_id, template in ENTERPRISE_TEMPLATES.items()
    ]


def apply_enterprise_template(body: AgentIntakeCreate, *, actor_sub: str) -> AgentIntakeCreate:
    if body.creation_path != "enterprise_template":
        return body

    template_id = body.template_id or "tmpl_support_agent"
    template = ENTERPRISE_TEMPLATES.get(template_id)
    if template is None:
        raise ValueError(f"unknown enterprise template: {template_id}")

    contract_defaults = template["contract"]
    contract_updates: dict[str, Any] = {}
    for field, default in contract_defaults.items():
        current = getattr(body.contract, field)
        if isinstance(current, list):
            contract_updates[field] = current or list(default)
        else:
            contract_updates[field] = current.strip() if current.strip() else default
    if not body.contract.owner_user_id.strip():
        contract_updates["owner_user_id"] = actor_sub
    if not body.contract.backup_owner_user_id.strip():
        contract_updates["backup_owner_user_id"] = ""

    template_artifacts = [
        AgentIntakeArtifactInput(**artifact) for artifact in template["artifacts"]
    ]
    artifacts = [*template_artifacts, *body.artifacts]
    capabilities = body.capabilities or list(template["capabilities"])
    return body.model_copy(
        update={
            "template_id": template_id,
            "contract": body.contract.model_copy(update=contract_updates),
            "artifacts": artifacts,
            "capabilities": capabilities,
        }
    )


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


_TOOL_ARTIFACT_KINDS: set[ArtifactKind] = {
    "openapi",
    "postman",
    "curl",
    "devtools_fetch",
}

_KNOWLEDGE_ARTIFACT_KINDS: set[ArtifactKind] = {
    "pdf",
    "faq",
    "runbook",
    "transcript",
    "botpress_export",
    "dialogflow_export",
    "rasa_export",
    "zendesk_export",
    "intercom_export",
    "other",
}


def _label_from_url(value: str) -> str:
    parsed = urlparse(value)
    host = (parsed.hostname or "").split(".")[0]
    path = next(
        (
            part
            for part in parsed.path.split("/")
            if part and not re.fullmatch(r"v\d+", part.lower())
        ),
        "",
    )
    parts = [part for part in [host, path if path != host else "", "api"] if part]
    return " ".join(parts) or value


def _first_url(value: str) -> str:
    match = re.search(r"https?://[^\s'\"),]+", value)
    return match.group(0) if match else ""


def _artifact_tool_label(artifact: AgentIntakeArtifactInput) -> str:
    text = artifact.text.strip()
    source = artifact.source_ref.strip()
    raw = text or source or artifact.name

    if artifact.kind in {"curl", "devtools_fetch"}:
        url = _first_url(raw)
        if url:
            return _label_from_url(url)

    if artifact.kind == "postman" and text:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict) and str(parsed.get("name", "")).strip():
            return str(parsed["name"]).strip()
        info = parsed.get("info") if isinstance(parsed, dict) else None
        if isinstance(info, dict) and str(info.get("name", "")).strip():
            return str(info["name"]).strip()

    if artifact.kind == "openapi" and text:
        title = re.search(r'(?im)^\s*title\s*:\s*["\']?([^"\'\n]+)', text)
        if title:
            return title.group(1).strip()
        quoted = re.search(r'"title"\s*:\s*"([^"]+)"', text)
        if quoted:
            return quoted.group(1).strip()

    url = _first_url(raw)
    if url:
        return _label_from_url(url)
    return re.sub(r"\.[A-Za-z0-9]{2,8}$", "", artifact.name).replace("_", " ")


def _system_tool_candidates(body: CommitmentBody) -> list[dict[str, Any]]:
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
                "source": "contract:systems_touched",
                "source_artifact": "",
                "import_mode": "manual_system",
                "promotion_blocker": "Live mode requires owner review and failure behavior.",
            }
        )
    return tools


def _artifact_tool_candidates(
    body: CommitmentBody,
    artifacts: list[AgentIntakeArtifactInput],
) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for artifact in artifacts:
        if artifact.kind not in _TOOL_ARTIFACT_KINDS:
            continue
        label = _artifact_tool_label(artifact)
        tool_id = f"mock_{_normalise_token(label)}"
        tools.append(
            {
                "tool_id": tool_id,
                "name": f"{_display(label)} draft tool",
                "description": (
                    f"Sandbox contract inferred from {artifact.kind} artifact "
                    f"{artifact.name}; live credentials are not required for first proof."
                ),
                "side_effect_level": "read",
                "sandbox_status": "mock",
                "owner_user_id": body.owner_user_id,
                "source": f"artifact:{artifact.kind}",
                "source_artifact": artifact.source_ref or artifact.name,
                "import_mode": artifact.kind,
                "promotion_blocker": (
                    "Review side effects, auth, schemas, and failure behavior before live use."
                ),
            }
        )
    return tools


def candidate_tool_specs(body: AgentIntakeCreate) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for tool in [
        *_system_tool_candidates(body.contract),
        *_artifact_tool_candidates(body.contract, body.artifacts),
    ]:
        deduped.setdefault(str(tool["tool_id"]), tool)
    return list(deduped.values())


def _knowledge_content_type(kind: ArtifactKind) -> str:
    if kind == "pdf":
        return "application/pdf"
    if kind in {"botpress_export", "dialogflow_export", "rasa_export"}:
        return "application/json"
    if kind in {"zendesk_export", "intercom_export"}:
        return "application/zip"
    if kind == "transcript":
        return "text/csv"
    return "text/plain"


def candidate_knowledge_sources(body: AgentIntakeCreate) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for artifact in body.artifacts:
        if artifact.kind not in _KNOWLEDGE_ARTIFACT_KINDS:
            continue
        text = artifact.text.strip()
        source_ref = artifact.source_ref.strip()
        byte_size = len((text or source_ref or artifact.name).encode("utf-8"))
        rows.append(
            {
                "id": f"knowledge_{_normalise_token(artifact.name)}",
                "name": artifact.name,
                "kind": artifact.kind,
                "source_ref": source_ref or artifact.name,
                "status": "ready_for_ingestion"
                if text or source_ref
                else "needs_content",
                "content_type": _knowledge_content_type(artifact.kind),
                "byte_size": byte_size,
                "coverage_hint": (
                    "conversation examples"
                    if artifact.kind == "transcript"
                    else "policy and procedure grounding"
                ),
                "evidence_ref": source_ref or f"intake-artifact/{artifact.name}",
            }
        )
    return rows


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


_CHANNEL_ARTIFACT_ALIASES: dict[str, tuple[str, ...]] = {
    "web_chat": ("web_chat", "web chat", "webchat", "embed snippet"),
    "whatsapp": ("whatsapp", "whats app", "wa_business"),
    "telegram": ("telegram", "telegram bot"),
    "slack": ("slack", "slack app", "slash command"),
    "teams": ("teams", "microsoft teams", "ms teams"),
    "sms": ("sms channel", "text message channel", "twilio sms"),
    "email": ("email channel", "inbox routing", "zendesk email"),
    "voice": ("voice channel", "phone channel", "call channel", "sip", "twilio voice"),
    "webhook_api": ("webhook", "api channel", "signed request"),
}


def _channel_key(value: str) -> str:
    normalised = value.strip().lower().replace("-", "_").replace(" ", "_")
    if normalised in {"web", "chat", "webchat"}:
        return "web_chat"
    if normalised in {"api", "webhook"}:
        return "webhook_api"
    return normalised


def _artifact_channel_candidates(
    artifacts: list[AgentIntakeArtifactInput],
    *,
    seen: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for artifact in artifacts:
        haystack = " ".join(
            [artifact.name, artifact.kind, artifact.source_ref, artifact.text]
        ).lower()
        for channel, aliases in _CHANNEL_ARTIFACT_ALIASES.items():
            if channel in seen:
                continue
            if not any(alias in haystack for alias in aliases):
                continue
            rows.append(
                {
                    "channel": channel,
                    "status": "draft",
                    "readiness": (
                        "Channel inferred from intake artifact; production "
                        "identity, transcript capture, and handoff checks are pending."
                    ),
                    "source": f"artifact:{artifact.kind}",
                    "source_artifact": artifact.source_ref or artifact.name,
                }
            )
            seen.add(channel)
    return rows


def candidate_channel_specs(body: AgentIntakeCreate) -> list[dict[str, Any]]:
    contract_channels = _candidate_channels(body.contract)
    seen = {_channel_key(str(item["channel"])) for item in contract_channels}
    return [
        *contract_channels,
        *_artifact_channel_candidates(body.artifacts, seen=seen),
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
    candidate_tools = candidate_tool_specs(body)
    knowledge_sources = candidate_knowledge_sources(body)
    candidate_channels = candidate_channel_specs(body)
    candidate_eval_cases = _candidate_eval_cases(body.contract)
    ready = [
        "Mission defined",
        "Commitment Document drafted",
        f"{len(candidate_eval_cases)} starter evals created",
    ]
    if created_object_refs.get("version_id"):
        ready.append("Initial behavior generated")
    if created_object_refs.get("branch_id"):
        ready.append("Draft branch main/draft created")
    if candidate_channels:
        ready.append(f"{len(candidate_channels)} sandbox channel binding(s) created")
    if candidate_tools:
        ready.append(f"{len(candidate_tools)} mock tool contract(s) created")
    if knowledge_sources:
        ready.append(f"{len(knowledge_sources)} knowledge source candidate(s) captured")
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
        candidate_knowledge_sources=knowledge_sources,
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
