"""Studio connect flow for RCS Business Messaging."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class RcsBrandProfile(_StrictModel):
    workspace_id: str
    brand_id: str
    display_name: str
    agent_id: str
    webhook_base_url: str
    regions: tuple[str, ...] = Field(default=("global",), min_length=1)


class RcsConnectResult(_StrictModel):
    brand_id: str
    agent_id: str
    webhook_url: str
    verification_status: str
    ready: bool


class RcsProvisioner(Protocol):
    def verify_brand(self, profile: RcsBrandProfile) -> str: ...

    def configure_webhook(self, *, agent_id: str, webhook_url: str) -> None: ...


class RcsConnectFlow:
    def __init__(self, provisioner: RcsProvisioner) -> None:
        self._provisioner = provisioner

    def connect(self, profile: RcsBrandProfile) -> RcsConnectResult:
        if not profile.webhook_base_url.startswith("https://"):
            raise ValueError("RCS webhook_base_url must be https")
        status = self._provisioner.verify_brand(profile)
        webhook_url = f"{profile.webhook_base_url.rstrip('/')}/channels/rcs/webhook"
        self._provisioner.configure_webhook(agent_id=profile.agent_id, webhook_url=webhook_url)
        return RcsConnectResult(
            brand_id=profile.brand_id,
            agent_id=profile.agent_id,
            webhook_url=webhook_url,
            verification_status=status,
            ready=status == "verified",
        )


__all__ = ["RcsBrandProfile", "RcsConnectFlow", "RcsConnectResult", "RcsProvisioner"]
