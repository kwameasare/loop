"""Studio connect flow for WhatsApp Business Cloud API."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict

CLOUD_API_VERSION = "v20.0"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class WhatsAppBusinessAccount(_StrictModel):
    waba_id: str
    phone_number_id: str
    display_phone_number: str
    verified_name: str


class WhatsAppConnectRequest(_StrictModel):
    workspace_id: str
    access_token_secret_ref: str
    webhook_base_url: str
    verify_token_secret_ref: str
    waba_id: str | None = None


class WhatsAppConnectResult(_StrictModel):
    workspace_id: str
    cloud_api_version: str
    phone_number_id: str
    webhook_url: str
    ready: bool


class WhatsAppProvisioner(Protocol):
    def list_accounts(self, access_token_secret_ref: str) -> tuple[WhatsAppBusinessAccount, ...]: ...

    def subscribe_webhook(
        self,
        *,
        phone_number_id: str,
        webhook_url: str,
        verify_token_secret_ref: str,
    ) -> None: ...


class WhatsAppConnectFlow:
    def __init__(self, provisioner: WhatsAppProvisioner) -> None:
        self._provisioner = provisioner

    def connect(self, request: WhatsAppConnectRequest) -> WhatsAppConnectResult:
        if not request.webhook_base_url.startswith("https://"):
            raise ValueError("webhook_base_url must be https")
        accounts = self._provisioner.list_accounts(request.access_token_secret_ref)
        selected = _select_account(accounts, request.waba_id)
        webhook_url = f"{request.webhook_base_url.rstrip('/')}/channels/whatsapp/webhook"
        self._provisioner.subscribe_webhook(
            phone_number_id=selected.phone_number_id,
            webhook_url=webhook_url,
            verify_token_secret_ref=request.verify_token_secret_ref,
        )
        return WhatsAppConnectResult(
            workspace_id=request.workspace_id,
            cloud_api_version=CLOUD_API_VERSION,
            phone_number_id=selected.phone_number_id,
            webhook_url=webhook_url,
            ready=True,
        )


def _select_account(
    accounts: tuple[WhatsAppBusinessAccount, ...],
    waba_id: str | None,
) -> WhatsAppBusinessAccount:
    for account in accounts:
        if waba_id is None or account.waba_id == waba_id:
            return account
    raise ValueError("no matching WhatsApp Business Account")


__all__ = [
    "CLOUD_API_VERSION",
    "WhatsAppBusinessAccount",
    "WhatsAppConnectFlow",
    "WhatsAppConnectRequest",
    "WhatsAppConnectResult",
    "WhatsAppProvisioner",
]
