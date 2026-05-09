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
            ("tenant_installed", "Tenant installed"),
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
            ("endpoint_verified", "Endpoint verified"),
            ("signature_verified", "Signature verification configured"),
            ("retry_policy", "Retry policy tested"),
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


def _payload(record: ChannelBindingRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


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


def channel_binding_payload(record: ChannelBindingRecord) -> dict[str, Any]:
    return _payload(record)
