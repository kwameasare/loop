from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from loop_control_plane._app_agents import AgentRecord
from loop_control_plane.workspaces import WorkspaceError

SECRET_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
ALLOWED_REF_PREFIXES = (
    "kms://",
    "vault://",
    "aws-sm://",
    "gcp-sm://",
    "azure-kv://",
    "hashicorp-vault://",
    "arn:",
)


class AgentSecretRefCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1, max_length=128)
    ref: str = Field(min_length=1, max_length=512)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not SECRET_NAME_RE.match(value):
            raise ValueError("secret name must be SCREAMING_SNAKE_CASE")
        return value

    @field_validator("ref")
    @classmethod
    def validate_ref(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("secret ref is required")
        if not trimmed.startswith(ALLOWED_REF_PREFIXES):
            raise ValueError(
                "secret ref must point to a supported vault or KMS provider"
            )
        return trimmed


class AgentSecretRefRotate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    ref: str | None = Field(default=None, min_length=1, max_length=512)

    @field_validator("ref")
    @classmethod
    def validate_ref(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return AgentSecretRefCreate.validate_ref(value)


class AgentSecretRefRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    id: str
    workspace_id: UUID
    agent_id: UUID
    name: str
    ref: str
    created_at: datetime
    rotated_at: datetime | None = None


def agent_secret_ref_payload(record: AgentSecretRefRecord) -> dict[str, Any]:
    return record.model_dump(mode="json", exclude={"workspace_id"})


def agent_secret_ref_audit_payload(record: AgentSecretRefRecord) -> dict[str, Any]:
    return {
        "agent_id": str(record.agent_id),
        "name": record.name,
        "ref_kind": _ref_kind(record.ref),
        "rotated_at": record.rotated_at.isoformat() if record.rotated_at else None,
    }


def _ref_kind(ref: str) -> str:
    if ref.startswith("arn:"):
        return "arn"
    return ref.split("://", maxsplit=1)[0]


class AgentSecretRefRegistry:
    """Agent-scoped secret reference metadata.

    The registry stores only vault/KMS references. It deliberately does not
    read, write, or mirror plaintext secret values from the workspace secret
    backend, because Studio's agent Secrets tab is governance evidence, not a
    credential exfiltration path.
    """

    def __init__(self) -> None:
        self._by_agent: dict[UUID, list[AgentSecretRefRecord]] = {}
        self._lock = asyncio.Lock()

    async def list_for_agent(self, *, agent: AgentRecord) -> list[AgentSecretRefRecord]:
        async with self._lock:
            return list(self._by_agent.get(agent.id, []))

    async def create(
        self,
        *,
        agent: AgentRecord,
        body: AgentSecretRefCreate,
    ) -> AgentSecretRefRecord:
        async with self._lock:
            refs = self._by_agent.setdefault(agent.id, [])
            if any(ref.name == body.name for ref in refs):
                raise WorkspaceError(f"secret ref already exists: {body.name}")
            record = AgentSecretRefRecord(
                id=f"sec_{uuid4().hex[:12]}",
                workspace_id=agent.workspace_id,
                agent_id=agent.id,
                name=body.name,
                ref=body.ref,
                created_at=datetime.now(UTC),
            )
            refs.insert(0, record)
            return record

    async def get(self, *, secret_id: str) -> AgentSecretRefRecord:
        async with self._lock:
            for refs in self._by_agent.values():
                for record in refs:
                    if record.id == secret_id:
                        return record
        raise WorkspaceError(f"unknown secret ref: {secret_id}")

    async def rotate(
        self,
        *,
        secret_id: str,
        body: AgentSecretRefRotate,
    ) -> AgentSecretRefRecord:
        async with self._lock:
            for agent_id, refs in self._by_agent.items():
                for index, record in enumerate(refs):
                    if record.id != secret_id:
                        continue
                    updated = record.model_copy(
                        update={
                            "ref": body.ref or record.ref,
                            "rotated_at": datetime.now(UTC),
                        }
                    )
                    refs[index] = updated
                    self._by_agent[agent_id] = refs
                    return updated
        raise WorkspaceError(f"unknown secret ref: {secret_id}")


__all__ = [
    "AgentSecretRefCreate",
    "AgentSecretRefRecord",
    "AgentSecretRefRegistry",
    "AgentSecretRefRotate",
    "agent_secret_ref_audit_payload",
    "agent_secret_ref_payload",
]
