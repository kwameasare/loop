---
name: update-threat-model
description: Use whenever a change introduces a new attack surface — new public endpoint, new channel, new MCP tool, new integration, new auth flow.
when_to_use: |
  - Adding a public endpoint that didn't exist.
  - Adding a channel adapter.
  - Adding an MCP tool with novel egress patterns.
  - Changing how secrets are stored, rotated, or accessed.
  - Touching audit-log integrity.
required_reading:
  - engineering/SECURITY.md
  - architecture/AUTH_FLOWS.md
  - architecture/NETWORKING.md
  - adrs/README.md   # ADR-016, ADR-020
applies_to: security
owner: Sec/Compliance Eng (hire #8)
last_reviewed: 2026-04-29
---

# Update threat model

## Trigger

Any change that creates a new attack surface or changes a trust boundary.

## Required reading

1. `engineering/SECURITY.md` §1 (trust boundaries) and §2 (STRIDE).
2. `architecture/AUTH_FLOWS.md` and `architecture/NETWORKING.md`.

## Steps

1. **Identify the surface.** Where does untrusted input enter? Where does sensitive data exit?
2. **Walk STRIDE** for the new surface: Spoofing / Tampering / Repudiation / Info-disclosure / DoS / Elevation. For each, document the threat + vector + mitigation.
3. **Update `engineering/SECURITY.md`** in the relevant subsection (§2.1 runtime, §2.2 sandbox, §2.3 channels, §2.4 auth/API, §2.5 exfiltration). Add rows; never delete past entries (history matters).
4. **Cross-reference ADRs** when the mitigation invokes a decision — e.g., ADR-020 (RLS), ADR-016 (cloud-agnostic = no leaky cloud SDKs).
5. **Tests:** every new threat row gets at least one test that proves the mitigation. Negative test (the threat in action) → it's blocked.
6. **Update audit-log scope** (`engineering/SECURITY.md` §7.1) if your change adds an admin-relevant action — apply `security/add-audit-event.md`.
7. **Run a tabletop**: walk a hypothetical attacker through the surface in a 30-min team exercise. Capture what they'd try; verify the model covers it.
8. **PR:** apply `meta/write-pr.md`. Tag Sec eng + CTO.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] STRIDE-walk in PR description.
- [ ] `engineering/SECURITY.md` row(s) added.
- [ ] Mitigation referenced an ADR or runbook.
- [ ] Negative test in place.
- [ ] Audit-log scope updated if applicable.
- [ ] Tabletop run + notes captured.

## Anti-patterns

- ❌ "It's behind the gateway, we're fine."
- ❌ Trusting external input without validation.
- ❌ "Authenticated == authorized."
- ❌ Logging sensitive request bodies.

## Related skills

- `security/add-audit-event.md`, `security/secrets-kms-check.md`, `security/add-error-code.md`.

## References

- `engineering/SECURITY.md`.
- `architecture/AUTH_FLOWS.md`, `architecture/NETWORKING.md`.
