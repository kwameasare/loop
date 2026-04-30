"""Tests for Loop-layer phone number provisioning (S049)."""

from __future__ import annotations

import pytest
from loop_voice import (
    InMemoryPhoneNumberProvisioner,
    PhoneCapability,
    PhoneNumberCandidate,
    PhoneNumberProvisioner,
    PhoneNumberSearchQuery,
    PhoneNumberStatus,
    PhoneProvisioningError,
    validate_e164,
)


def _candidate(
    e164: str,
    *,
    carrier: str = "twilio",
    caps: tuple[PhoneCapability, ...] = (
        PhoneCapability.VOICE,
        PhoneCapability.SMS,
    ),
    country: str = "US",
) -> PhoneNumberCandidate:
    return PhoneNumberCandidate(
        e164=e164,
        country=country,
        carrier=carrier,
        capabilities=caps,
        monthly_cost_usd=1.0,
    )


@pytest.fixture
def provisioner() -> InMemoryPhoneNumberProvisioner:
    return InMemoryPhoneNumberProvisioner(
        inventory=(
            _candidate("+14155550100"),
            _candidate("+14155550101"),
            _candidate("+14085550200"),
            _candidate("+442071838750", country="GB"),
        )
    )


def test_validate_e164_accepts_well_formed() -> None:
    assert validate_e164("+14155550100") == "+14155550100"


def test_validate_e164_rejects_bad() -> None:
    with pytest.raises(PhoneProvisioningError):
        validate_e164("415-555-0100")


async def test_search_filters_by_country(
    provisioner: InMemoryPhoneNumberProvisioner,
) -> None:
    out = await provisioner.search(PhoneNumberSearchQuery(country="GB"))
    assert len(out) == 1 and out[0].e164.startswith("+44")


async def test_search_filters_by_area_code(
    provisioner: InMemoryPhoneNumberProvisioner,
) -> None:
    out = await provisioner.search(
        PhoneNumberSearchQuery(country="US", area_code="415")
    )
    assert {c.e164 for c in out} == {"+14155550100", "+14155550101"}


async def test_search_respects_capabilities(
    provisioner: InMemoryPhoneNumberProvisioner,
) -> None:
    out = await provisioner.search(
        PhoneNumberSearchQuery(
            country="US",
            capabilities=(PhoneCapability.MMS,),
        )
    )
    assert out == ()


async def test_buy_assigns_id_and_marks_active(
    provisioner: InMemoryPhoneNumberProvisioner,
) -> None:
    cands = await provisioner.search(PhoneNumberSearchQuery(country="US"))
    bought = await provisioner.buy(
        cands[0], tenant_id="tnt_a", agent_id="ag_1"
    )
    assert bought.id.startswith("pn_")
    assert bought.status == PhoneNumberStatus.ACTIVE
    assert bought.agent_id == "ag_1"
    assert bought.acquired_at is not None


async def test_buy_rejects_unknown_candidate(
    provisioner: InMemoryPhoneNumberProvisioner,
) -> None:
    with pytest.raises(PhoneProvisioningError, match="not in carrier"):
        await provisioner.buy(
            _candidate("+19995550000"), tenant_id="tnt_a"
        )


async def test_buy_is_idempotent_against_double_purchase(
    provisioner: InMemoryPhoneNumberProvisioner,
) -> None:
    cands = await provisioner.search(PhoneNumberSearchQuery(country="GB"))
    await provisioner.buy(cands[0], tenant_id="tnt_a")
    # second buy of the same candidate should fail (inventory drained)
    with pytest.raises(PhoneProvisioningError):
        await provisioner.buy(cands[0], tenant_id="tnt_a")


async def test_assign_updates_agent(
    provisioner: InMemoryPhoneNumberProvisioner,
) -> None:
    cands = await provisioner.search(PhoneNumberSearchQuery(country="US"))
    bought = await provisioner.buy(cands[0], tenant_id="tnt_a")
    reassigned = await provisioner.assign(bought.id, agent_id="ag_2")
    assert reassigned.agent_id == "ag_2"


async def test_assign_unknown_raises(
    provisioner: InMemoryPhoneNumberProvisioner,
) -> None:
    with pytest.raises(PhoneProvisioningError, match="unknown number"):
        await provisioner.assign("pn_999999", agent_id="ag_1")


async def test_release_marks_released(
    provisioner: InMemoryPhoneNumberProvisioner,
) -> None:
    cands = await provisioner.search(PhoneNumberSearchQuery(country="US"))
    bought = await provisioner.buy(cands[0], tenant_id="tnt_a")
    released = await provisioner.release(bought.id)
    assert released.status == PhoneNumberStatus.RELEASED
    assert released.agent_id is None
    assert released.released_at is not None


async def test_release_twice_raises(
    provisioner: InMemoryPhoneNumberProvisioner,
) -> None:
    cands = await provisioner.search(PhoneNumberSearchQuery(country="US"))
    bought = await provisioner.buy(cands[0], tenant_id="tnt_a")
    await provisioner.release(bought.id)
    with pytest.raises(PhoneProvisioningError, match="already released"):
        await provisioner.release(bought.id)


async def test_list_active_scopes_to_tenant(
    provisioner: InMemoryPhoneNumberProvisioner,
) -> None:
    cands = await provisioner.search(PhoneNumberSearchQuery(country="US"))
    await provisioner.buy(cands[0], tenant_id="tnt_a")
    await provisioner.buy(cands[1], tenant_id="tnt_b")
    active_a = await provisioner.list_active(tenant_id="tnt_a")
    assert len(active_a) == 1


def test_in_memory_implements_protocol(
    provisioner: InMemoryPhoneNumberProvisioner,
) -> None:
    p: PhoneNumberProvisioner = provisioner
    assert p is provisioner
