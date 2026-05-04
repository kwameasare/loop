"""Pass12 WhatsApp connect-flow tests."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from loop_channels_whatsapp import (
    CLOUD_API_VERSION,
    WhatsAppBusinessAccount,
    WhatsAppConnectFlow,
    WhatsAppConnectRequest,
)


def test_whatsapp_connect_flow_subscribes_selected_waba() -> None:
    provisioner = _FakeWhatsAppProvisioner()
    result = WhatsAppConnectFlow(provisioner).connect(
        WhatsAppConnectRequest(
            workspace_id="ws",
            access_token_secret_ref="wa-token",
            webhook_base_url="https://loop.example",
            verify_token_secret_ref="wa-verify-token",
            waba_id="waba-2",
        )
    )
    assert result.ready
    assert result.cloud_api_version == CLOUD_API_VERSION
    assert result.phone_number_id == "phone-2"
    assert provisioner.subscribed == (
        "phone-2",
        "https://loop.example/channels/whatsapp/webhook",
        "wa-verify-token",
    )


def test_whatsapp_connect_requires_https() -> None:
    with pytest.raises(ValueError):
        WhatsAppConnectFlow(_FakeWhatsAppProvisioner()).connect(
            WhatsAppConnectRequest(
                workspace_id="ws",
                access_token_secret_ref="wa-token",
                webhook_base_url="http://loop.local",
                verify_token_secret_ref="wa-verify-token",
            )
        )


@dataclass(slots=True)
class _FakeWhatsAppProvisioner:
    subscribed: tuple[str, str, str] | None = None

    def list_accounts(self, access_token_secret_ref: str) -> tuple[WhatsAppBusinessAccount, ...]:
        assert access_token_secret_ref == "wa-token"
        return (
            WhatsAppBusinessAccount(
                waba_id="waba-1",
                phone_number_id="phone-1",
                display_phone_number="+15550000001",
                verified_name="Loop One",
            ),
            WhatsAppBusinessAccount(
                waba_id="waba-2",
                phone_number_id="phone-2",
                display_phone_number="+15550000002",
                verified_name="Loop Two",
            ),
        )

    def subscribe_webhook(
        self,
        *,
        phone_number_id: str,
        webhook_url: str,
        verify_token_secret_ref: str,
    ) -> None:
        self.subscribed = (phone_number_id, webhook_url, verify_token_secret_ref)
