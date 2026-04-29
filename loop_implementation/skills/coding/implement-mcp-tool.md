---
name: implement-mcp-tool
description: Use when adding or modifying an MCP tool — either an in-process Python function (auto-MCP'd via decorator) or an out-of-process MCP server in a Firecracker sandbox.
when_to_use: |
  - Adding a `@tool` Python function to an example agent.
  - Publishing an MCP server to the Loop Hub.
  - Modifying the tool dispatcher (`dp-tool-host`).
  - Changing tool sandbox isolation (Firecracker / Kata) — this requires an ADR.
  - Adding tool egress allow-list rules.
required_reading:
  - architecture/ARCHITECTURE.md      # §3.2 components (Tool/MCP layer)
  - architecture/CLOUD_PORTABILITY.md # §3 mapping for Firecracker/Kata
  - architecture/AUTH_FLOWS.md        # §10 customer-supplied MCP servers
  - architecture/NETWORKING.md        # §3 egress, §10 customer MCP connectivity
  - data/SCHEMA.md                    # §2.3 mcp_servers + agent_tool_grants
  - engineering/SECURITY.md           # §2.2 sandbox threat model
  - engineering/ERROR_CODES.md        # TH prefix
  - adrs/README.md                    # ADR-003, ADR-005, ADR-021
applies_to: coding
owner: Founding Eng #1 (Runtime)
last_reviewed: 2026-04-29
---

# Implement MCP tool

## Trigger

You are adding or modifying a tool an agent can call. Loop's tool ABI is **MCP** (ADR-003) — never a custom action format.

## Required reading

1. `architecture/ARCHITECTURE.md` §3 (component diagram).
2. `engineering/SECURITY.md` §2.2 (sandbox threat model — must satisfy every mitigation).
3. ADR-003 (MCP universal ABI), ADR-005 (Firecracker), ADR-021 (Kata + Firecracker for sandbox).

## Steps

### Path A: in-process auto-MCP'd Python function

Use this when the tool is part of the agent's own code and the agent owns it (trusted).

1. Add a function decorated with `@tool` from `loop.sdk`:
   ```python
   from loop.sdk import tool

   @tool
   async def lookup_order(order_id: str) -> dict:
       """Look up an order. Returns status + estimated delivery.

       Args are validated against type hints; the docstring is the tool description
       the LLM sees. Pydantic types in args/return become the JSON schema.
       """
       ...
   ```
2. Type hints become the input schema. Use Pydantic models for nested types.
3. Docstring becomes the LLM-facing description. Keep it factual; agents read it to decide when to call the tool.
4. Register in the agent's `tools = [Tool.fn(lookup_order), ...]` list.
5. Tests: at least one unit test of the function itself, one test that runs the agent with a fixture LLM that calls the tool.

### Path B: out-of-process MCP server (Firecracker sandboxed)

Use this when the tool is third-party code, customer-supplied, or needs strong isolation.

1. Implement the MCP server per the [MCP spec](https://modelcontextprotocol.io). Use the official Python SDK if you can.
2. Container image: minimal Alpine or Distroless base. No interactive shells. Pin every dep version.
3. Manifest (`mcp.toml` or `manifest.json`):
   - `tools`: list with name, description, input_schema, optional output_schema.
   - `egress_allowlist`: list of FQDNs the tool may reach. Default deny.
   - `resource_limits`: cpu, memory, fd, max-runtime-seconds.
4. Register in the Loop Hub via `loop mcp publish`. The Hub signs the image and stores it in OCI.
5. Customer installs via `loop mcp install loop-hub://<name>@<version>`. The runtime grants the agent access via `agent_tool_grants` with an allow-list of which tools.
6. Sandbox: never bypass Firecracker for an out-of-process tool. Cold start should land in the prewarmed pool ≤ 100ms.

### Tool dispatcher changes (`dp-tool-host`)

Only modify if you're a runtime engineer and your change has an ADR.

1. Maintains the Firecracker pool size + warm queue.
2. Schedules tool invocations across pool, returns results to the runtime via NATS subject `TOOLS.result.<workspace>.<agent>.<turn>`.
3. Enforces resource limits (cgroup) and egress allow-lists (network policy).
4. Surfaces `LOOP-TH-NNN` errors back to the runtime per `engineering/ERROR_CODES.md`.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Tool conforms to MCP (manifest validated against the schema).
- [ ] Egress allow-list specified (default deny).
- [ ] Resource limits set (cpu, memory, fd, runtime).
- [ ] No cross-workspace state in the tool (sandbox is ephemeral).
- [ ] In-process tools: `@tool` decorator, type hints, docstring.
- [ ] Hub-published tools: signed image, semver tag.
- [ ] Tests: unit + integration with the agent calling the tool.
- [ ] Docs: if a built-in Loop tool, mention it in `architecture/ARCHITECTURE.md` §9.2 list.
- [ ] If tool persists state outside its sandbox lifetime, that's an ADR.

## Anti-patterns

- ❌ Custom tool format that isn't MCP.
- ❌ Sharing a sandbox across workspaces.
- ❌ Skipping the egress allow-list — every tool gets one.
- ❌ Running an out-of-process tool in-process "because it's faster." Trust boundary lost.
- ❌ Logging tool args/results without PII redaction.
- ❌ Letting a tool exceed `max_runtime_seconds`.

## Related skills

- `coding/implement-runtime-feature.md` (if you're changing the dispatcher).
- `security/secrets-kms-check.md` (if the tool needs creds).
- `observability/add-otel-span.md` (every tool call gets a span).
- `devrel/publish-mcp-server.md` (Hub publishing flow).

## References

- ADR-003 (MCP), ADR-005 (Firecracker), ADR-021 (Kata + Firecracker).
- `engineering/SECURITY.md` §2.2.
- `engineering/ERROR_CODES.md` §"TH".
