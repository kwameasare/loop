from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_agents import AgentRecord
from loop_control_plane.workspaces import WorkspaceError

ChannelType = Literal[
    "web_chat",
    "whatsapp",
    "telegram",
    "slack",
    "teams",
    "sms",
    "email",
    "voice",
    "webhook_api",
]
ChannelStatus = Literal[
    "not_configured",
    "draft",
    "ready",
    "staged",
    "live",
    "paused",
    "error",
    "archived",
]
ReadinessStatus = Literal["pending", "passed", "failed", "not_required"]
RequiredConfigStatus = Literal[
    "configured",
    "missing",
    "pending_verification",
    "blocked",
]

SUPPORTED_CHANNELS: tuple[ChannelType, ...] = (
    "web_chat",
    "whatsapp",
    "telegram",
    "slack",
    "teams",
    "sms",
    "email",
    "voice",
    "webhook_api",
)


class ChannelBindingUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel_type: ChannelType
    provider: str = Field(default="loop", max_length=120)
    display_name: str = Field(default="", max_length=160)
    status: ChannelStatus = "draft"
    identity_config: dict[str, Any] = Field(default_factory=dict)
    auth_config_ref: str | None = Field(default=None, max_length=240)


class ChannelReadinessUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ReadinessStatus
    evidence_ref: str | None = Field(default=None, max_length=240)
    message: str = Field(default="", max_length=500)


class ChannelActivityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["success", "failure"] = "success"
    trace_id: str = Field(default="", max_length=256)
    occurred_at: datetime | None = None
    failure_message: str = Field(default="", max_length=500)


class ChannelPreviewMatrixRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_title: str = Field(default="Duplicate charge", min_length=1, max_length=180)
    user_message: str = Field(
        default="I was charged twice for my renewal. What happens now?",
        min_length=1,
        max_length=1000,
    )
    expected_outcome: str = Field(
        default="Acknowledge the duplicate charge, verify the account, explain the refund path, and offer escalation.",
        min_length=1,
        max_length=2000,
    )
    channel_types: list[ChannelType] = Field(default_factory=list, max_length=9)


class ChannelPreviewEvalCaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_title: str = Field(min_length=1, max_length=180)
    channel_type: ChannelType
    binding_id: str = Field(min_length=1, max_length=120)
    user_message: str = Field(min_length=1, max_length=1000)
    rendered_preview: str = Field(min_length=1, max_length=4000)
    expected_outcome: str = Field(min_length=1, max_length=2000)
    failure_reason: str = Field(min_length=1, max_length=1000)
    source_ref: str = Field(default="channel-preview-matrix", max_length=512)


class ChannelBindingRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    workspace_id: UUID
    agent_id: UUID
    channel_type: ChannelType
    provider: str
    display_name: str
    status: ChannelStatus
    identity_config: dict[str, Any]
    auth_config_ref: str | None
    readiness: list[dict[str, Any]]
    last_traffic_at: datetime | None = None
    last_failure_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


def _display_name(channel_type: ChannelType) -> str:
    return {
        "web_chat": "Web chat",
        "whatsapp": "WhatsApp",
        "telegram": "Telegram",
        "slack": "Slack",
        "teams": "Teams",
        "sms": "SMS",
        "email": "Email",
        "voice": "Voice",
        "webhook_api": "Webhook/API",
    }[channel_type]


def _default_provider(channel_type: ChannelType) -> str:
    return {
        "web_chat": "Loop Web",
        "whatsapp": "Twilio or Meta Cloud API",
        "telegram": "Telegram Bot API",
        "slack": "Slack Platform",
        "teams": "Microsoft Teams",
        "sms": "Twilio SMS",
        "email": "Loop Mail Router",
        "voice": "LiveKit + Twilio",
        "webhook_api": "Signed HTTPS",
    }[channel_type]


def _readiness_template(channel_type: ChannelType) -> list[dict[str, Any]]:
    checks: dict[ChannelType, list[tuple[str, str]]] = {
        "web_chat": [
            ("domain_verified", "Domain verified"),
            ("snippet_minted", "Snippet minted"),
            ("test_conversation", "Test conversation passed"),
            ("trace_capture", "Trace capture enabled"),
        ],
        "whatsapp": [
            ("business_verified", "Business identity verified"),
            ("template_approved", "Template approved"),
            ("test_inbound", "Test inbound message passed"),
            ("handoff_route", "Handoff route configured"),
        ],
        "telegram": [
            ("token_verified", "Bot token verified"),
            ("test_command", "Test command passed"),
            ("trace_capture", "Trace capture enabled"),
        ],
        "slack": [
            ("workspace_installed", "Workspace installed"),
            ("test_mention", "Test mention passed"),
            ("thread_reply", "Thread reply passed"),
            ("permissions_approved", "Permissions approved"),
        ],
        "teams": [
            ("workspace_installed", "Workspace installed"),
            ("test_mention", "Test mention passed"),
            ("thread_reply", "Thread reply passed"),
            ("permissions_approved", "Permissions approved"),
        ],
        "sms": [
            ("number_active", "Number active"),
            ("opt_out_verified", "Opt-out verified"),
            ("test_message", "Test message passed"),
        ],
        "email": [
            ("sender_verified", "Sender verified"),
            ("inbound_tested", "Inbound route tested"),
            ("reply_tested", "Reply route tested"),
        ],
        "voice": [
            ("number_provisioned", "Number provisioned"),
            ("test_call", "Test call passed"),
            ("asr_tts_spans", "ASR/TTS spans captured"),
            ("transfer_route", "Transfer route tested"),
        ],
        "webhook_api": [
            ("signed_request", "Signed request verified"),
            ("retry_behavior", "Retry behavior tested"),
            ("trace_capture", "Trace capture enabled"),
        ],
    }
    return [
        {
            "id": check_id,
            "label": label,
            "status": "pending",
            "evidence_ref": None,
            "message": "",
        }
        for check_id, label in checks[channel_type]
    ]


def _required_config_template(channel_type: ChannelType) -> list[dict[str, Any]]:
    templates: dict[ChannelType, list[dict[str, Any]]] = {
        "web_chat": [
            {
                "id": "embed_snippet",
                "label": "Embed snippet",
                "source": "readiness",
                "readiness_id": "snippet_minted",
            },
            {
                "id": "domain_allowlist",
                "label": "Domain allowlist",
                "source": "identity_config",
                "keys": ["domain_allowlist", "domain"],
            },
            {
                "id": "theme",
                "label": "Theme",
                "source": "identity_config",
                "keys": ["theme", "theme_id"],
            },
            {
                "id": "session_identity",
                "label": "Session identity",
                "source": "identity_config",
                "keys": ["session_identity", "identity"],
            },
            {
                "id": "handoff_route",
                "label": "Handoff route",
                "source": "identity_config",
                "keys": ["handoff_route", "handoff_queue"],
            },
            {
                "id": "transcript_capture",
                "label": "Transcript capture",
                "source": "readiness",
                "readiness_id": "trace_capture",
            },
        ],
        "whatsapp": [
            {
                "id": "business_account",
                "label": "Business account",
                "source": "identity_config",
                "keys": ["business_account_id", "business_account", "handle"],
            },
            {
                "id": "provider_connection",
                "label": "Provider connection",
                "source": "auth_config_ref",
            },
            {
                "id": "template_approvals",
                "label": "Template approvals",
                "source": "readiness",
                "readiness_id": "template_approved",
            },
            {
                "id": "session_window_policy",
                "label": "Session window policy",
                "source": "identity_config",
                "keys": ["session_window_policy"],
            },
            {
                "id": "media_policy",
                "label": "Media policy",
                "source": "identity_config",
                "keys": ["media_policy"],
            },
            {
                "id": "opt_in_out_policy",
                "label": "Opt-in/out policy",
                "source": "identity_config",
                "keys": ["opt_in_out_policy", "opt_policy"],
            },
        ],
        "telegram": [
            {
                "id": "bot_token",
                "label": "Bot token",
                "source": "auth_config_ref",
            },
            {
                "id": "command_policy",
                "label": "Command policy",
                "source": "identity_config",
                "keys": ["command_policy"],
            },
            {
                "id": "group_direct_policy",
                "label": "Group/direct policy",
                "source": "identity_config",
                "keys": ["group_direct_policy"],
            },
            {
                "id": "attachment_policy",
                "label": "Attachment policy",
                "source": "identity_config",
                "keys": ["attachment_policy"],
            },
            {
                "id": "abuse_controls",
                "label": "Abuse controls",
                "source": "identity_config",
                "keys": ["abuse_controls"],
            },
        ],
        "slack": [
            {
                "id": "workspace_installation",
                "label": "Workspace installation",
                "source": "readiness",
                "readiness_id": "workspace_installed",
            },
            {
                "id": "mention_policy",
                "label": "Mention policy",
                "source": "identity_config",
                "keys": ["mention_policy"],
            },
            {
                "id": "thread_policy",
                "label": "Thread policy",
                "source": "identity_config",
                "keys": ["thread_policy"],
            },
            {
                "id": "slash_commands",
                "label": "Slash commands",
                "source": "identity_config",
                "keys": ["slash_commands"],
            },
            {
                "id": "internal_identity_mapping",
                "label": "Internal identity mapping",
                "source": "identity_config",
                "keys": ["identity_mapping", "internal_identity_mapping"],
            },
            {
                "id": "private_channel_policy",
                "label": "Private channel policy",
                "source": "identity_config",
                "keys": ["private_channel_policy"],
            },
        ],
        "teams": [
            {
                "id": "workspace_installation",
                "label": "Workspace installation",
                "source": "readiness",
                "readiness_id": "workspace_installed",
            },
            {
                "id": "mention_policy",
                "label": "Mention policy",
                "source": "identity_config",
                "keys": ["mention_policy"],
            },
            {
                "id": "thread_policy",
                "label": "Thread policy",
                "source": "identity_config",
                "keys": ["thread_policy"],
            },
            {
                "id": "slash_commands",
                "label": "Slash commands",
                "source": "identity_config",
                "keys": ["slash_commands"],
            },
            {
                "id": "internal_identity_mapping",
                "label": "Internal identity mapping",
                "source": "identity_config",
                "keys": ["identity_mapping", "internal_identity_mapping"],
            },
            {
                "id": "private_channel_policy",
                "label": "Private channel policy",
                "source": "identity_config",
                "keys": ["private_channel_policy"],
            },
        ],
        "sms": [
            {
                "id": "number",
                "label": "Number",
                "source": "identity_config",
                "keys": ["phone_number", "number"],
            },
            {
                "id": "provider",
                "label": "Provider",
                "source": "provider",
            },
            {
                "id": "opt_out_policy",
                "label": "Opt-out policy",
                "source": "readiness",
                "readiness_id": "opt_out_verified",
            },
            {
                "id": "carrier_compliance",
                "label": "Carrier compliance",
                "source": "identity_config",
                "keys": ["carrier_compliance"],
            },
            {
                "id": "message_length_policy",
                "label": "Message length policy",
                "source": "identity_config",
                "keys": ["message_length_policy"],
            },
        ],
        "email": [
            {
                "id": "inbox",
                "label": "Inbox",
                "source": "identity_config",
                "keys": ["inbox", "inbound_address"],
            },
            {
                "id": "sender_identity",
                "label": "Sender identity",
                "source": "readiness",
                "readiness_id": "sender_verified",
            },
            {
                "id": "routing_rules",
                "label": "Routing rules",
                "source": "identity_config",
                "keys": ["routing_rules"],
            },
            {
                "id": "attachment_policy",
                "label": "Attachment policy",
                "source": "identity_config",
                "keys": ["attachment_policy"],
            },
            {
                "id": "sla_policy",
                "label": "SLA policy",
                "source": "identity_config",
                "keys": ["sla_policy", "sla"],
            },
            {
                "id": "signature_policy",
                "label": "Signature policy",
                "source": "identity_config",
                "keys": ["signature_policy"],
            },
        ],
        "voice": [
            {
                "id": "phone_number",
                "label": "Phone number",
                "source": "readiness",
                "readiness_id": "number_provisioned",
            },
            {
                "id": "asr_provider",
                "label": "ASR provider",
                "source": "identity_config",
                "keys": ["asr_provider"],
            },
            {
                "id": "tts_provider",
                "label": "TTS provider",
                "source": "identity_config",
                "keys": ["tts_provider"],
            },
            {
                "id": "barge_in_policy",
                "label": "Barge-in policy",
                "source": "identity_config",
                "keys": ["barge_in_policy"],
            },
            {
                "id": "transfer_policy",
                "label": "Transfer policy",
                "source": "identity_config",
                "keys": ["transfer_policy"],
            },
            {
                "id": "recording_policy",
                "label": "Recording policy",
                "source": "identity_config",
                "keys": ["recording_policy"],
            },
            {
                "id": "latency_budget",
                "label": "Latency budget",
                "source": "identity_config",
                "keys": ["latency_budget"],
            },
        ],
        "webhook_api": [
            {
                "id": "endpoint",
                "label": "Endpoint",
                "source": "identity_config",
                "keys": ["endpoint_url", "endpoint"],
            },
            {
                "id": "auth",
                "label": "Auth",
                "source": "auth_config_ref",
            },
            {
                "id": "signature_verification",
                "label": "Signature verification",
                "source": "readiness",
                "readiness_id": "signed_request",
            },
            {
                "id": "retry_policy",
                "label": "Retry policy",
                "source": "readiness",
                "readiness_id": "retry_behavior",
            },
            {
                "id": "idempotency_key",
                "label": "Idempotency key",
                "source": "identity_config",
                "keys": ["idempotency_key"],
            },
            {
                "id": "rate_limits",
                "label": "Rate limits",
                "source": "identity_config",
                "keys": ["rate_limits", "rate_limit"],
            },
        ],
    }
    return templates[channel_type]


def _configured_identity_value(
    identity_config: dict[str, Any],
    keys: list[str],
) -> tuple[str | None, str | None]:
    for key in keys:
        value = identity_config.get(key)
        if isinstance(value, str) and value.strip():
            return key, value.strip()
        if value is not None and not isinstance(value, (dict, list)):
            return key, str(value)
        if isinstance(value, (dict, list)) and value:
            return key, "configured"
    return None, None


def _readiness_by_id(record: ChannelBindingRecord) -> dict[str, dict[str, Any]]:
    return {str(check.get("id", "")): check for check in record.readiness}


def _required_config(record: ChannelBindingRecord) -> list[dict[str, Any]]:
    readiness = _readiness_by_id(record)
    required: list[dict[str, Any]] = []
    for item in _required_config_template(record.channel_type):
        source = str(item["source"])
        status: RequiredConfigStatus = "missing"
        evidence_ref: str | None = None
        key: str | None = None
        value_summary = ""
        if source == "provider":
            status = "configured" if record.provider else "missing"
            value_summary = record.provider or ""
        elif source == "auth_config_ref":
            status = "configured" if record.auth_config_ref else "missing"
            evidence_ref = record.auth_config_ref
            value_summary = "Secret reference bound" if record.auth_config_ref else ""
        elif source == "identity_config":
            key, value_summary = _configured_identity_value(
                record.identity_config,
                list(item.get("keys", [])),
            )
            status = "configured" if key else "missing"
            value_summary = value_summary or ""
        elif source == "readiness":
            check = readiness.get(str(item["readiness_id"]))
            check_status = str(check.get("status", "pending")) if check else "pending"
            evidence_ref = str(check.get("evidence_ref") or "") if check else None
            if check_status == "passed":
                status = "configured"
            elif check_status == "failed":
                status = "blocked"
            else:
                status = "pending_verification"
            value_summary = str(check.get("message") or "") if check else ""
        required.append(
            {
                "id": item["id"],
                "label": item["label"],
                "status": status,
                "source": source,
                "key": (
                    key
                    or item.get("readiness_id")
                    or item.get("key")
                    or next(iter(item.get("keys", [])), source)
                ),
                "evidence_ref": evidence_ref or None,
                "value_summary": value_summary,
            }
        )
    return required


def _binding_id(agent: AgentRecord, channel_type: ChannelType) -> str:
    return f"cb_{agent.id.hex[:8]}_{channel_type}"


def _default_binding(agent: AgentRecord, channel_type: ChannelType) -> ChannelBindingRecord:
    now = datetime.now(UTC)
    return ChannelBindingRecord(
        id=_binding_id(agent, channel_type),
        workspace_id=agent.workspace_id,
        agent_id=agent.id,
        channel_type=channel_type,
        provider=_default_provider(channel_type),
        display_name=_display_name(channel_type),
        status="not_configured",
        identity_config={},
        auth_config_ref=None,
        readiness=_readiness_template(channel_type),
        created_at=now,
        updated_at=now,
    )


def channel_readiness_state(binding: ChannelBindingRecord) -> str:
    required = [item for item in binding.readiness if item.get("status") != "not_required"]
    if binding.status == "not_configured":
        return "not_configured"
    if not required:
        return "ready"
    if any(item.get("status") == "failed" for item in required):
        return "blocked"
    if all(item.get("status") == "passed" for item in required):
        return "ready"
    return "needs_readiness"


def _readiness_summary(record: ChannelBindingRecord) -> dict[str, Any]:
    required = [item for item in record.readiness if item.get("status") != "not_required"]
    passed = [item for item in required if item.get("status") == "passed"]
    failed = [item for item in required if item.get("status") == "failed"]
    pending = [item for item in required if item.get("status") == "pending"]
    return {
        "state": channel_readiness_state(record),
        "passed": len(passed),
        "failed": len(failed),
        "pending": len(pending),
        "total": len(required),
        "blocking_check_ids": [
            str(item.get("id", ""))
            for item in required
            if item.get("status") in {"failed", "pending"}
        ],
    }


def _payload(record: ChannelBindingRecord) -> dict[str, Any]:
    payload = record.model_dump(mode="json")
    payload["required_config"] = _required_config(record)
    payload["readiness_summary"] = _readiness_summary(record)
    return payload


def channel_required_config(record: ChannelBindingRecord) -> list[dict[str, Any]]:
    return _required_config(record)


class ChannelBindingRegistry:
    def __init__(self) -> None:
        self._items: dict[UUID, dict[ChannelType, ChannelBindingRecord]] = {}
        self._lock = asyncio.Lock()

    async def list_for_agent(self, *, agent: AgentRecord) -> list[ChannelBindingRecord]:
        async with self._lock:
            configured = self._items.get(agent.id, {})
            return [
                configured.get(channel_type) or _default_binding(agent, channel_type)
                for channel_type in SUPPORTED_CHANNELS
            ]

    async def upsert(
        self,
        *,
        agent: AgentRecord,
        body: ChannelBindingUpsert,
    ) -> ChannelBindingRecord:
        async with self._lock:
            now = datetime.now(UTC)
            by_channel = self._items.setdefault(agent.id, {})
            previous = by_channel.get(body.channel_type)
            readiness = (
                previous.readiness
                if previous is not None
                else _readiness_template(body.channel_type)
            )
            record = ChannelBindingRecord(
                id=previous.id if previous is not None else _binding_id(agent, body.channel_type),
                workspace_id=agent.workspace_id,
                agent_id=agent.id,
                channel_type=body.channel_type,
                provider=body.provider,
                display_name=body.display_name or _display_name(body.channel_type),
                status=body.status,
                identity_config=body.identity_config,
                auth_config_ref=body.auth_config_ref,
                readiness=readiness,
                last_traffic_at=previous.last_traffic_at if previous is not None else None,
                last_failure_at=previous.last_failure_at if previous is not None else None,
                created_at=previous.created_at if previous is not None else now,
                updated_at=now,
            )
            by_channel[body.channel_type] = record
            return record

    async def set_readiness(
        self,
        *,
        agent: AgentRecord,
        binding_id: str,
        check_id: str,
        body: ChannelReadinessUpdate,
    ) -> ChannelBindingRecord:
        async with self._lock:
            by_channel = self._items.get(agent.id, {})
            for channel_type, record in by_channel.items():
                if record.id != binding_id:
                    continue
                found = False
                readiness: list[dict[str, Any]] = []
                for check in record.readiness:
                    if check.get("id") == check_id:
                        found = True
                        readiness.append(
                            {
                                **check,
                                "status": body.status,
                                "evidence_ref": body.evidence_ref,
                                "message": body.message,
                            }
                        )
                    else:
                        readiness.append(check)
                if not found:
                    raise WorkspaceError(f"unknown readiness check: {check_id}")
                required = [
                    item for item in readiness if item.get("status") not in {"not_required"}
                ]
                status: ChannelStatus = (
                    "ready"
                    if required and all(item.get("status") == "passed" for item in required)
                    else record.status
                )
                now = datetime.now(UTC)
                updated = record.model_copy(
                    update={"readiness": readiness, "status": status, "updated_at": now}
                )
                by_channel[channel_type] = updated
                return updated
        raise WorkspaceError(f"unknown channel binding: {binding_id}")

    async def record_activity(
        self,
        *,
        agent: AgentRecord,
        binding_id: str,
        body: ChannelActivityCreate,
    ) -> ChannelBindingRecord:
        async with self._lock:
            now = datetime.now(UTC)
            occurred_at = body.occurred_at or now
            by_channel = self._items.setdefault(agent.id, {})
            configured = self._items.get(agent.id, {})
            for channel_type in SUPPORTED_CHANNELS:
                record = configured.get(channel_type) or _default_binding(agent, channel_type)
                if record.id != binding_id:
                    continue
                updated = record.model_copy(
                    update={
                        "last_traffic_at": occurred_at,
                        "last_failure_at": (
                            occurred_at
                            if body.status == "failure"
                            else record.last_failure_at
                        ),
                        "updated_at": now,
                    }
                )
                by_channel[channel_type] = updated
                return updated
        raise WorkspaceError(f"unknown channel binding: {binding_id}")


def channel_binding_payload(record: ChannelBindingRecord) -> dict[str, Any]:
    return _payload(record)
