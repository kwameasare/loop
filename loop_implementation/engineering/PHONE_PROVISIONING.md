# Phone number provisioning (S049)

Loop sits in front of multiple telephony carriers (Twilio, Telnyx,
Vonage, Bandwidth) and presents one consistent surface to agent
authors. This document is the contract for that surface.

## Why this lives at the Loop layer

- **Portability** — switching a tenant's underlying carrier (cost,
  outage, regulatory) must not require reconfiguring agents.
- **Compliance** — number ownership, KYC docs, and porting consent
  are tenant-scoped and audited; carrier accounts are an
  implementation detail.
- **Pricing transparency** — Loop lists numbers with a marked-up
  monthly rate, never the raw carrier rate.

## Lifecycle

```
                ┌──────────────┐  buy     ┌────────────┐
                │  AVAILABLE   ├─────────▶│  ACTIVE    │
                │  (carrier    │          │  (Loop-    │
                │   inventory) │          │   owned)   │
                └──────────────┘          └─────┬──────┘
                                                │ release
                                                ▼
                                          ┌────────────┐
                                          │  RELEASED  │
                                          └────────────┘
```

Intermediate states `PROVISIONING`, `RELEASING`, and `PORTING_OUT`
exist for the carrier round-trip; production adapters use them while
in-memory tests collapse straight to the terminal state.

## Code surface

`loop_voice.phone` (see
[phone.py](../scaffolding/packages/voice/loop_voice/phone.py)):

| Symbol                            | Purpose                                      |
| --------------------------------- | -------------------------------------------- |
| `PhoneCapability`                 | StrEnum: voice, sms, mms, fax                |
| `PhoneNumberStatus`               | Lifecycle StrEnum                            |
| `PhoneNumberSearchQuery`          | Strict pydantic search input                 |
| `PhoneNumberCandidate`            | Carrier-side offer (not yet bought)          |
| `PhoneNumber`                     | Loop-owned, tenant-scoped record             |
| `PhoneNumberProvisioner`          | Protocol every adapter implements            |
| `InMemoryPhoneNumberProvisioner`  | Test double, drives unit + studio dev runner |
| `validate_e164`                   | Strict E.164 parser                          |
| `PhoneProvisioningError`          | Carrier or policy error                      |

## API mapping (preview, lands with S049b)

| HTTP                                  | Method on `PhoneNumberProvisioner` |
| ------------------------------------- | ---------------------------------- |
| `GET /v1/phone/search?country=US`     | `search(query)`                    |
| `POST /v1/phone/buy`                  | `buy(candidate, tenant_id=…)`      |
| `PATCH /v1/phone/{id}/assign`         | `assign(number_id, agent_id=…)`    |
| `DELETE /v1/phone/{id}`               | `release(number_id)`               |
| `GET /v1/phone?status=active`         | `list_active(tenant_id)`           |

## Carrier adapter rules

- Adapters **must** be stateless beyond a per-instance auth context;
  state lives in Loop's Postgres `phone_numbers` table.
- Errors **must** raise `PhoneProvisioningError` — no carrier-native
  exception types may leak past the adapter boundary.
- Idempotency: `buy()` is keyed on `(carrier, e164)`; replays after
  a network failure must not double-provision.

## Out of scope

- **Inbound porting** (`PORT_IN`) — handled by S076 (Q3 deliverable).
- **Number compliance docs** (FCC 499-A, CRTC, OFCOM forms) — uploaded
  through the Studio Compliance screen, persisted separately.
- **Per-call routing rules** — owned by `loop_voice.session`, not
  this module.
