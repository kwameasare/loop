---
name: implement-cli-command
description: Use when adding or modifying a `loop` CLI subcommand. Triggers on changes under cli/ (Go).
when_to_use: |
  - Adding a new top-level subcommand (`loop X`).
  - Adding flags or arguments to an existing subcommand.
  - Implementing local-mode behavior (e.g., `loop dev`, `loop tail`).
  - Changing auth/credential storage logic (`~/.loop/credentials`).
required_reading:
  - engineering/HANDBOOK.md       # §2.3 Go conventions
  - architecture/AUTH_FLOWS.md    # §3 CLI auth (device-flow, API key)
  - api/openapi.yaml              # endpoints the CLI calls
  - engineering/ENV_REFERENCE.md  # §11 CLI env vars
applies_to: coding
owner: Founding Eng #5 (Studio) — secondary CLI owner; original = Eng #1 + Eng #2 jointly
last_reviewed: 2026-04-29
---

# Implement CLI command

## Trigger

Touching `cli/`. The CLI is the most-used Loop surface for builders; UX matters.

## Required reading

1. `engineering/HANDBOOK.md` §2.3 (Go conventions — cobra, viper, golangci-lint, no global state).
2. `architecture/AUTH_FLOWS.md` §3 (device-flow + API-key auth).
3. `api/openapi.yaml` for the endpoint shapes.

## Steps

1. **Decide:** is this a top-level subcommand (`loop X`) or a sub-subcommand (`loop X Y`)? Keep the top level small (< 15 commands).
2. **Cobra command file:** `cli/cmd/<name>.go`. One file per command. Use `init()` to register on the parent.
3. **Flags via viper:** flags must also be settable via `LOOP_<COMMAND>_<FLAG>` env vars and `~/.loop/config.yaml`.
4. **Default profile:** `loop` reads the `default` profile from `~/.loop/profiles.yaml`. The `--profile` flag overrides. Profile carries auth + region + workspace.
5. **Output format:** every command supports `--output` with `text` (default), `json`, `yaml`. JSON output is the canonical contract for scripting.
6. **Error handling:** wrap with `fmt.Errorf("%w: ...", err)`. CLI exit codes:
   - 0 = success.
   - 1 = generic failure.
   - 2 = usage error (bad flags).
   - 3 = auth error.
   - 4 = network / API error.
   - 5 = local config error.
7. **Telemetry:** anonymous opt-in (`LOOP_NO_TELEMETRY=true` to disable). Captures command name, exit code, duration. Never captures args / values.
8. **Long-running commands** (`loop dev`, `loop tail`, `loop eval run`): handle SIGINT/SIGTERM gracefully; print final summary line on exit.
9. **Tests:**
   - Table-tested unit tests for command parsing.
   - Integration test using a mock cp-api (httptest) for happy + auth-fail + network-fail.
10. **Documentation:** every command supports `loop X --help` with examples. Add an `examples:` block in the cobra registration.
11. **Release artifact:** ensure `release.yml` builds for ubuntu-latest, macos-latest, windows-latest.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Command in `cli/cmd/<name>.go`.
- [ ] Flags work via flag, env, config file.
- [ ] `--output text|json|yaml` supported.
- [ ] Exit codes per the table above.
- [ ] Help text with examples.
- [ ] Long-running variants handle signals.
- [ ] Telemetry respects opt-out.
- [ ] Tests: table + integration.
- [ ] `golangci-lint run` clean.

## Anti-patterns

- ❌ Subcommands that read stdin without explicit `-` flag (UX surprise).
- ❌ Hidden side effects (writing files outside `~/.loop/`).
- ❌ Hard-coded server URLs. Always go through the resolved profile.
- ❌ Telemetry that captures argument values.
- ❌ Pretty-printing as the default — JSON for scripts is the contract.

## Related skills

- `api/update-openapi.md` if you change the API the CLI relies on.
- `testing/write-integration-test.md`.

## References

- `engineering/HANDBOOK.md` §2.3.
- `architecture/AUTH_FLOWS.md` §3.
- `engineering/ENV_REFERENCE.md` §11.
