"""Studio connect flow for Twilio SMS numbers."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class TwilioNumberCandidate(_StrictModel):
    phone_number: str
    friendly_name: str
    capabilities: tuple[str, ...] = ("SMS",)


class TwilioConnectRequest(_StrictModel):
    workspace_id: str
    account_sid: str
    auth_token_secret_ref: str
    webhook_base_url: str
    selected_number: str | None = None


class TwilioConnectResult(_StrictModel):
    workspace_id: str
    phone_number: str
    inbound_webhook_url: str
    status_callback_url: str
    ready: bool


class TwilioProvisioner(Protocol):
    def list_numbers(self, account_sid: str) -> tuple[TwilioNumberCandidate, ...]: ...

    def configure_number(
        self,
        *,
        account_sid: str,
        phone_number: str,
        inbound_webhook_url: str,
        status_callback_url: str,
    ) -> None: ...


class TwilioConnectFlow:
    def __init__(self, provisioner: TwilioProvisioner) -> None:
        self._provisioner = provisioner

    def connect(self, request: TwilioConnectRequest) -> TwilioConnectResult:
        if not request.webhook_base_url.startswith("https://"):
            raise ValueError("webhook_base_url must be https")
        numbers = self._provisioner.list_numbers(request.account_sid)
        selected = request.selected_number or _first_sms_number(numbers)
        inbound = f"{request.webhook_base_url.rstrip('/')}/channels/sms/twilio/inbound"
        status = f"{request.webhook_base_url.rstrip('/')}/channels/sms/twilio/status"
        self._provisioner.configure_number(
            account_sid=request.account_sid,
            phone_number=selected,
            inbound_webhook_url=inbound,
            status_callback_url=status,
        )
        return TwilioConnectResult(
            workspace_id=request.workspace_id,
            phone_number=selected,
            inbound_webhook_url=inbound,
            status_callback_url=status,
            ready=True,
        )


def _first_sms_number(numbers: tuple[TwilioNumberCandidate, ...]) -> str:
    for number in numbers:
        if "SMS" in number.capabilities:
            return number.phone_number
    raise ValueError("no SMS-capable Twilio number available")


__all__ = [
    "TwilioConnectFlow",
    "TwilioConnectRequest",
    "TwilioConnectResult",
    "TwilioNumberCandidate",
    "TwilioProvisioner",
]
