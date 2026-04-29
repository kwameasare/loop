---
name: publish-mcp-server
description: Use when publishing an MCP server to the Loop Hub.
when_to_use: |
  - First-party Loop tools (Stripe, GitHub, Salesforce, Zendesk, ...).
  - Community-contributed servers being featured in the Hub.
required_reading:
  - skills/coding/implement-mcp-tool.md
  - architecture/ARCHITECTURE.md     # §3.2 tool layer
  - engineering/SECURITY.md           # §2.2 sandbox
applies_to: devrel
owner: Eng #6 (DevRel)
last_reviewed: 2026-04-29
---

# Publish MCP server

## Trigger

Adding a server to the Loop Hub catalog.

## Required reading

`skills/coding/implement-mcp-tool.md`.

## Steps

1. **Conform to MCP spec** (Path B in `coding/implement-mcp-tool.md`).
2. **Manifest invariants:**
   - Distinctive `name`.
   - Semver tag.
   - `tools[]` with input/output schemas.
   - `egress_allowlist` (default deny).
   - `resource_limits` (cpu, memory, fd, runtime).
3. **Container image:** distroless or Alpine. No interactive shell. Pin every dep.
4. **Image signing:** Hub signs on publish (cosign). Customers verify on install.
5. **Documentation page** under `docs/hub/<server>/`:
   - Lede + use cases.
   - Tool list with examples.
   - Required secrets (env vars in Vault, never hard-coded).
   - Limitations (egress, rate limits, costs).
6. **CHANGELOG** alongside the server.
7. **License** declared in manifest. Default for first-party = Apache 2.0; community can pick any OSI-approved.
8. **Publish:** `loop mcp publish ./<server-dir> --version <semver>`.
9. **Hub listing:** add to `apps/docs/hub/index.md` with category.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Manifest valid against schema.
- [ ] Image signed.
- [ ] Egress allow-list explicit.
- [ ] Resource limits set.
- [ ] Docs page with examples.
- [ ] CHANGELOG entry.
- [ ] License declared.
- [ ] Listed in Hub index.

## Anti-patterns

- ❌ Tools that exfiltrate to undeclared egress.
- ❌ Hard-coded secrets.
- ❌ Manifest without resource limits.
- ❌ Latest tags ("v1") that move; always immutable semver.

## Related skills

- `coding/implement-mcp-tool.md`, `security/secrets-kms-check.md`.

## References

- `architecture/ARCHITECTURE.md` §3.2.
- `engineering/SECURITY.md` §2.2.
