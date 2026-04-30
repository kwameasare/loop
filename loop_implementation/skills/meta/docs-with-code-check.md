---
name: docs-with-code-check
description: Use whenever you open a PR. Verifies that any code change touching schemas, env vars, error codes, or public types is paired with the corresponding `loop_implementation/` doc edit in the same PR.
when_to_use: |
  - Opening any PR.
  - Failing CI after a feature commit.
  - Reviewing someone else's PR for hygiene.
required_reading:
  - skills/meta/write-pr.md
  - skills/data/update-schema.md
  - skills/security/add-error-code.md
  - engineering/HANDBOOK.md  # §10 docs-with-code rule
applies_to: meta
owner: every PR author
last_reviewed: 2026-04-30
---

# Docs-with-code check

## Trigger

Before opening any PR. The CI gate runs automatically; this skill is what you reference when the gate fails.

## The rule

If your PR touches **any** of these code paths, it must also touch the listed doc(s) **in the same PR**. CI (`tools/check_docs_with_code.py`) enforces it.

| If you change … | You must update … |
|-----------------|-------------------|
| `packages/*/migrations/versions/*.py` (any new/changed migration) | `loop_implementation/data/SCHEMA.md` |
| `packages/sdk-py/loop/types.py` or any `_types.py` exported from a public package | `loop_implementation/data/SCHEMA.md` §9 + `loop_implementation/api/openapi.yaml` |
| Any `errors.py` introducing a new `code = "LOOP-XX-NNN"` class attr | `loop_implementation/engineering/ERROR_CODES.md` |
| Any new `LOOP_*` env-var read (`os.environ["LOOP_..."]`, `Settings(... = Field(env="LOOP_...")`, etc.) | `loop_implementation/engineering/ENV_REFERENCE.md` |
| Any new top-level service or container in `packages/` or `apps/` | `loop_implementation/architecture/ARCHITECTURE.md` §2 |
| Any new public REST endpoint or path in `apps/control-plane/cp_api/routes/` | `loop_implementation/api/openapi.yaml` |
| Any new ADR-warranting decision (see `architecture/propose-adr.md` triggers) | `loop_implementation/adrs/README.md` |
| Any new MCP server, KB source type, channel adapter, eval scorer | the relevant doc-section in ARCHITECTURE.md |

## Steps (when you're failing the gate)

1. **Read the failure output** — `check_docs_with_code.py` prints the offending file(s) and the doc(s) it expects updated.
2. **Don't disable the check.** If you genuinely don't need to update a doc, that's a bug in the rule. Open a PR that fixes the rule, not a PR that bypasses it.
3. **Apply the matching skill:**
   - Migration → `data/update-schema.md` §"Postgres tables".
   - New error code → `security/add-error-code.md`.
   - New env var → add a row to `ENV_REFERENCE.md` in the right section.
   - Public type change → `data/add-pydantic-type.md`.
4. **Re-run the gate locally** before pushing:
   ```bash
   python tools/check_docs_with_code.py --base origin/main --head HEAD
   ```
5. **Commit the doc edit** as the same logical commit (or as a follow-up commit on the branch — both are fine; no extra PR).

## Definition of done

- [ ] `tools/check_docs_with_code.py` passes against your branch.
- [ ] Each rule-violating file in your diff has its paired doc-file edited.
- [ ] PR description doesn't claim "docs follow in a separate PR" — that's not allowed.

## Anti-patterns

- ❌ Adding `# noqa: docs-with-code` or any other bypass mechanism.
- ❌ "I'll do the docs in S0NN+1" — never. Same PR.
- ❌ Marking the docs-updated checkbox in `meta/write-pr.md` without actually editing the docs.
- ❌ Editing the doc with a placeholder like "TODO: describe this table" — write the real content.

## Related skills

- `meta/write-pr.md` (this gate is in the pre-merge checklist).
- `data/update-schema.md`, `security/add-error-code.md`, `data/add-pydantic-type.md`, `api/update-openapi.md`, `architecture/update-architecture.md`, `architecture/propose-adr.md` — the skills that satisfy the gate.

## References

- `engineering/HANDBOOK.md` §10 (docs-with-code is the canonical rule).
- `tools/check_docs_with_code.py` (the script the gate runs).
- `.github/workflows/ci.yml` — `docs-with-code` job.
